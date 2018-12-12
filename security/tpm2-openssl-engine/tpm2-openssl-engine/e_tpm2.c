/*
 * Copyright (c) 2017 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */
/* ====================================================================
 * Copyright (c) 1999-2001 The OpenSSL Project.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 *
 * 3. All advertising materials mentioning features or use of this
 *    software must display the following acknowledgment:
 *    "This product includes software developed by the OpenSSL Project
 *    for use in the OpenSSL Toolkit. (http://www.OpenSSL.org/)"
 *
 * 4. The names "OpenSSL Toolkit" and "OpenSSL Project" must not be used to
 *    endorse or promote products derived from this software without
 *    prior written permission. For written permission, please contact
 *    licensing@OpenSSL.org.
 *
 * 5. Products derived from this software may not be called "OpenSSL"
 *    nor may "OpenSSL" appear in their names without prior written
 *    permission of the OpenSSL Project.
 *
 * 6. Redistributions of any form whatsoever must retain the following
 *    acknowledgment:
 *    "This product includes software developed by the OpenSSL Project
 *    for use in the OpenSSL Toolkit (http://www.OpenSSL.org/)"
 *
 * THIS SOFTWARE IS PROVIDED BY THE OpenSSL PROJECT ``AS IS'' AND ANY
 * EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE OpenSSL PROJECT OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 * ====================================================================
 *
 * This product includes cryptographic software written by Eric Young
 * (eay@cryptsoft.com).  This product includes software written by Tim
 * Hudson (tjh@cryptsoft.com). 
 * This product is inspired by the original TPM 1.2 openssl engine written
 * by Kent Yoder <kyoder@users.sf.net> for the Trousers Project. This product
 * includes TPM key blob ASN-1 encoding scheme from James Bottomley
 * <james.bottomley@HansenPartnership.com> 
 *
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include <openssl/crypto.h>
#include <openssl/dso.h>
#include <openssl/engine.h>
#include <openssl/evp.h>
#include <openssl/objects.h>
#include <openssl/sha.h>
#include <openssl/bn.h>
#include <openssl/asn1.h>
#include <openssl/pem.h>

#include "e_tpm2.h"

#include "tpm2-asn.h"

//IMPLEMENT_ASN1_FUNCTIONS(TSSLOADABLE)

/* IBM TSS2 library functions */
static const char *TPM_F_File_ReadStructure = "TSS_File_ReadStructure";
static const char *TPM_F_Context_Create = "TSS_Create";
static const char *TPM_F_Context_Close = "TSS_Delete";
static const char *TPM_F_TPM_Execute = "TSS_Execute";
static const char *TPM_F_Hash_Generate = "TSS_Hash_Generate";
static const char *TPM_F_Structure_Marshal = "TSS_Structure_Marshal";
static const char *TPM_F_PrivateKey_Unmarshal = "TPM2B_PRIVATE_Unmarshal";
static const char *TPM_F_PublicKey_Unmarshal = "TPM2B_PUBLIC_Unmarshal";
static const char *TPM_F_Set_Property = "TSS_SetProperty";

/* engine specific functions */
static int tpm_engine_destroy(ENGINE *);
static int tpm_engine_init(ENGINE *);
static int tpm_engine_finish(ENGINE *);
static int tpm_engine_ctrl(ENGINE *, int, long, void *, void (*)());
static EVP_PKEY *tpm_engine_load_key(ENGINE *, const char *, UI_METHOD *, void *);
static int tpm_engine_flush_key_context(TPMI_DH_OBJECT hKey);

#ifndef OPENSSL_NO_RSA
/* rsa functions */
static int tpm_rsa_init(RSA *rsa);
static int tpm_rsa_finish(RSA *rsa);
static int tpm_rsa_priv_dec(int, const unsigned char *, unsigned char *, RSA *, int);
static int tpm_rsa_priv_enc(int, const unsigned char *, unsigned char *, RSA *, int);
#endif


/* The definitions for control commands specific to this engine */
#define TPM_CMD_SO_PATH     ENGINE_CMD_BASE
static const ENGINE_CMD_DEFN tpm_cmd_defns[] = {
    {TPM_CMD_SO_PATH,
     "SO_PATH",
     "Specifies the path to the libtpm2.so shared library",
     ENGINE_CMD_FLAG_STRING},
    {0, NULL, NULL, 0}
};

// for now we will only overwrite the RSA decryption
// operation to go over TPM 2.0.
// Add additional hooks as new use cases pop up
#ifndef OPENSSL_NO_RSA
static RSA_METHOD tpm_rsa = {
    "TPM 2.0 RSA method",     // name
    NULL,                     // rsa_pub_enc  (encrypt)                  
    NULL,                     // rsa_pub_dec  (verify arbitrary data)
    tpm_rsa_priv_enc,         // rsa_priv_enc (sign)
    tpm_rsa_priv_dec,         // rsa_priv_dec (decrypt)
    NULL,                     // rsa_mod_exp
    BN_mod_exp_mont,          // bn_mod_exp
    tpm_rsa_init,             // init
    tpm_rsa_finish,           // free
    (RSA_FLAG_SIGN_VER | RSA_FLAG_NO_BLINDING | RSA_FLAG_EXT_PKEY),
    NULL,                     // app_data
    NULL, /* sign */          // rsa_sign
    NULL, /* verify */        // rsa_verify
    NULL                      // rsa_keygen
};
#endif

/* Constants used when creating the ENGINE */
static const char *engine_tpm_id = "tpm2";
static const char *engine_tpm_name = "TPM 2.0 hardware engine support for";
static const char *TPM_LIBNAME = "tpm2";

static TSS_CONTEXT  *hContext    = NULL_HCONTEXT;
static TPMI_DH_OBJECT hKey = NULL_HKEY;
/* varibles used to get/set CRYPTO_EX_DATA values */
int  ex_app_data = TPM_ENGINE_EX_DATA_UNINIT;

/* This is a process-global DSO handle used for loading and unloading
 * the TSS library. NB: This is only set (or unset) during an
 * init() or finish() call (reference counts permitting) and they're
 * operating with global locks, so this should be thread-safe
 * implicitly. */

static DSO *tpm_dso = NULL;

/* These are the function pointers that are (un)set when the library has
 * successfully (un)loaded. */
static unsigned int (*p_tpm2_File_ReadStructure)();
static unsigned int (*p_tpm2_Context_Create)();
static unsigned int (*p_tpm2_Context_Close)();
static unsigned int (*p_tpm2_TPM_Execute)();
static unsigned int (*p_tpm2_Hash_Generate)();
static unsigned int (*p_tpm2_Structure_Marshal)();
static unsigned int (*p_tpm2_TPM_PrivateKey_Unmarshal)();
static unsigned int (*p_tpm2_TPM_PublicKey_Unmarshal)();
static unsigned int (*p_tpm2_Set_Property)();


/* This internal function is used by ENGINE_tpm() and possibly by the
 * "dynamic" ENGINE support too */
static int bind_helper(ENGINE * e)
{
#ifndef OPENSSL_NO_RSA
    const RSA_METHOD *meth1;
#endif
    if (!ENGINE_set_id(e, engine_tpm_id) ||
        !ENGINE_set_name(e, engine_tpm_name) ||
#ifndef OPENSSL_NO_RSA
        !ENGINE_set_RSA(e, &tpm_rsa) ||
#endif
        !ENGINE_set_destroy_function(e, tpm_engine_destroy) ||
        !ENGINE_set_init_function(e, tpm_engine_init) ||
        !ENGINE_set_finish_function(e, tpm_engine_finish) ||
        !ENGINE_set_ctrl_function(e, tpm_engine_ctrl) ||
        !ENGINE_set_load_privkey_function(e, tpm_engine_load_key) ||
        !ENGINE_set_cmd_defns(e, tpm_cmd_defns))
        return 0;

#ifndef OPENSSL_NO_RSA
    /* We know that the "PKCS1_SSLeay()" functions hook properly
     * to the tpm-specific mod_exp and mod_exp_crt so we use
     * those functions. NB: We don't use ENGINE_openssl() or
     * anything "more generic" because something like the RSAref
     * code may not hook properly, and if you own one of these
     * cards then you have the right to do RSA operations on it
     * anyway! */
    meth1 = RSA_PKCS1_SSLeay();
    if (meth1)
    {
        tpm_rsa.rsa_mod_exp = meth1->rsa_mod_exp;
        tpm_rsa.rsa_pub_enc = meth1->rsa_pub_enc;
        tpm_rsa.rsa_pub_dec = meth1->rsa_pub_dec;
    }
#endif

    /* Ensure the tpm error handling is set up */
    ERR_load_TPM_strings();
    return 1;
}

static ENGINE *engine_tpm(void)
{
    ENGINE *ret = ENGINE_new();
    if (!ret)
        return NULL;
    if (!bind_helper(ret)) {
        ENGINE_free(ret);
        return NULL;
    }
    return ret;
}

void ENGINE_load_tpm(void)
{
    /* Copied from eng_[openssl|dyn].c */
    ENGINE *toadd = engine_tpm();
    if (!toadd)
        return;
    ENGINE_add(toadd);
    ENGINE_free(toadd);
    ERR_clear_error();
}

/* Destructor (complements the "ENGINE_tpm()" constructor) */
static int tpm_engine_destroy(ENGINE * e)
{
    /* Unload the tpm error strings so any error state including our
     * functs or reasons won't lead to a segfault (they simply get displayed
     * without corresponding string data because none will be found). */
    ERR_unload_TPM_strings();
    return 1;
}

/* initialisation function */
static int tpm_engine_init(ENGINE * e)
{
    void (*p1) ();
    void (*p2) ();
    void (*p3) ();
    void (*p4) ();
    void (*p5) ();
    void (*p6) ();
    void (*p7) ();
    void (*p8) ();
    void (*p9) ();
    TPM_RC result;

    if (tpm_dso != NULL) {
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_ALREADY_LOADED);
        return 1;
    }

    if ((tpm_dso = DSO_load(NULL, TPM_LIBNAME, NULL, 0)) == NULL) {
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_DSO_FAILURE);
        goto err;
    }

    if (!(p1  = DSO_bind_func(tpm_dso, TPM_F_File_ReadStructure)) ||
        !(p2  = DSO_bind_func(tpm_dso, TPM_F_Context_Create)) ||
        !(p3  = DSO_bind_func(tpm_dso, TPM_F_Context_Close)) ||
        !(p4  = DSO_bind_func(tpm_dso, TPM_F_TPM_Execute)) ||
        !(p5  = DSO_bind_func(tpm_dso, TPM_F_Hash_Generate)) ||
        !(p6  = DSO_bind_func(tpm_dso, TPM_F_Structure_Marshal)) ||
        !(p7  = DSO_bind_func(tpm_dso, TPM_F_PrivateKey_Unmarshal)) ||
        !(p8  = DSO_bind_func(tpm_dso, TPM_F_PublicKey_Unmarshal)) ||
        !(p9  = DSO_bind_func(tpm_dso, TPM_F_Set_Property))
        ) {
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_DSO_FAILURE);
        goto err;
    }

    /* Copy the pointers */
    p_tpm2_File_ReadStructure = (unsigned int (*) ()) p1;
    p_tpm2_Context_Create = (unsigned int (*) ()) p2;
    p_tpm2_Context_Close = (unsigned int (*) ()) p3;
    p_tpm2_TPM_Execute = (unsigned int (*) ()) p4;
    p_tpm2_Hash_Generate = (unsigned int (*) ()) p5;
    p_tpm2_Structure_Marshal = (unsigned int (*) ()) p6;
    p_tpm2_TPM_PrivateKey_Unmarshal = (unsigned int (*) ()) p7;
    p_tpm2_TPM_PublicKey_Unmarshal = (unsigned int (*) ()) p8;
    p_tpm2_Set_Property = (unsigned int (*) ()) p9;

    if ((result = p_tpm2_Context_Create(&hContext))) {
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_UNIT_FAILURE);
        goto err;
    }

   /*
    * avoid using the tpm0 device TCTI as that will bind
    * exclusively to the TPM device. Instead
    * use the Kernel TPM Resource Manager as that
    * allows concurrent access
    *
    * N.B: This assumes that the kernel-modules-tpm
    * pkg is installed with the modified tpm_crb KLM
    */
    if ((result = p_tpm2_Set_Property(hContext, 
                    TPM_INTERFACE_TYPE, "dev"))) {
        DBG("Failed to set Resource Manager in context (%p): rc %d",
            hContext, (int)result);
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_UNIT_FAILURE);
        goto err;
    }

    if ((result = p_tpm2_Set_Property(hContext, 
                    TPM_DEVICE, "/dev/tpmrm0"))) {
        DBG("Failed to set Resource Manager in context (%p): rc %d",
            hContext, (int)result);
        TSSerr(TPM_F_TPM_ENGINE_INIT, TPM_R_UNIT_FAILURE);
        goto err;
    }

    return 1;
err:
    if (hContext != NULL_HCONTEXT) {
        p_tpm2_Context_Close(hContext);
        hContext = NULL_HCONTEXT;
    }

    if (tpm_dso) {
        DSO_free(tpm_dso);
        tpm_dso = NULL;
    }

    p_tpm2_File_ReadStructure = NULL;
    p_tpm2_Context_Create = NULL;
    p_tpm2_Context_Close = NULL;
    p_tpm2_TPM_Execute = NULL;
    p_tpm2_Hash_Generate = NULL;
    p_tpm2_Structure_Marshal = NULL;
    p_tpm2_TPM_PrivateKey_Unmarshal = NULL;
    p_tpm2_TPM_PublicKey_Unmarshal = NULL;
    p_tpm2_Set_Property = NULL;

    return 0;
}

static int tpm_engine_finish(ENGINE * e)
{
    if (tpm_dso == NULL) {
        TSSerr(TPM_F_TPM_ENGINE_FINISH, TPM_R_NOT_LOADED);
        return 0;
    }

    if (hKey != NULL_HKEY) {
        tpm_engine_flush_key_context(hKey);
        hKey = NULL_HKEY;
    }

    if (hContext != NULL_HCONTEXT) {
        p_tpm2_Context_Close(hContext);
        hContext = NULL_HCONTEXT;
    }

    if (!DSO_free(tpm_dso)) {
        TSSerr(TPM_F_TPM_ENGINE_FINISH, TPM_R_DSO_FAILURE);
        return 0;
    }
    tpm_dso = NULL;

    return 1;
}

int fill_out_rsa_object(RSA *rsa, TPMT_PUBLIC *pub, TPMI_DH_OBJECT hKey)
{
    struct rsa_app_data *app_data;
    unsigned long exp;

    if ((app_data = OPENSSL_malloc(sizeof(struct rsa_app_data))) == NULL) {
        TSSerr(TPM_F_TPM_FILL_RSA_OBJECT, ERR_R_MALLOC_FAILURE);
        return 0;
    }

    /* set e in the RSA object */
    if (!rsa->e && ((rsa->e = BN_new()) == NULL)) {
        TSSerr(TPM_F_TPM_FILL_RSA_OBJECT, ERR_R_MALLOC_FAILURE);
        return 0;
    }

    if (pub->parameters.rsaDetail.exponent == 0)
        exp = 65537;
    else
        exp = pub->parameters.rsaDetail.exponent;

    if (!BN_set_word(rsa->e, exp)) {
        TSSerr(TPM_F_TPM_FILL_RSA_OBJECT, TPM_R_REQUEST_FAILED);
        BN_free(rsa->e);
        return 0;
    }

    /* set n in the RSA object */
    if (!rsa->n && ((rsa->n = BN_new()) == NULL)) {
        TSSerr(TPM_F_TPM_FILL_RSA_OBJECT, ERR_R_MALLOC_FAILURE);
        BN_free(rsa->e);
        return 0;
    }
    
    if (!BN_bin2bn(pub->unique.rsa.t.buffer, pub->unique.rsa.t.size,
                   rsa->n)) {
        TSSerr(TPM_F_TPM_FILL_RSA_OBJECT, ERR_R_MALLOC_FAILURE);
        BN_free(rsa->e);
        BN_free(rsa->n);
        return 0;
    }

#if OPENSSL_VERSION_NUMBER >= 0x10100000
    RSA_set0_key(rsa, rsa->n, rsa->e, NULL);
#endif

    DBG("Setting hKey(0x%x) in RSA object", hKey);

    memset(app_data, 0, sizeof(struct rsa_app_data));
    app_data->hKey = hKey;
    RSA_set_ex_data(rsa, ex_app_data, app_data);

    return 1;
}

static int tpm_engine_flush_key_context(TPMI_DH_OBJECT hKey)
{
    TPM_RC rc;
    FlushContext_In input;
    
    if (hKey == NULL_HKEY) {
        TSSerr(TPM_F_TPM_FLUSH_OBJECT_CONTEXT, TPM_R_INVALID_KEY);
        return -1;
    }
    input.flushHandle = hKey;
    
    if ((rc = p_tpm2_TPM_Execute(hContext,
                                 NULL,
                                 (COMMAND_PARAMETERS *)&input,
                                 NULL,
                                 TPM_CC_FlushContext,
                                 TPM_RH_NULL, NULL, 0))) {
        DBG("Context Flush Failed: Ret code %d", rc);
        TSSerr(TPM_F_TPM_FLUSH_OBJECT_CONTEXT,
               TPM_R_REQUEST_FAILED);
        return -1;
    }

    return 0;
}

static EVP_PKEY *tpm_engine_load_key(ENGINE *e, const char *key_id,
                     UI_METHOD *ui, void *cb_data)
{
    RSA *rsa;
    EVP_PKEY *pkey;
    BIO *bf;
    char oid[128];
    TPM_RC rc;
    TSSLOADABLE *tssl;  // the TPM key
    Load_In input;
    Load_Out output;

    const char          *parentPassword = NULL;
    TPMI_SH_AUTH_SESSION        sessionHandle0 = TPM_RS_PW;
    unsigned int        sessionAttributes0 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle1 = TPM_RH_NULL;
    unsigned int        sessionAttributes1 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle2 = TPM_RH_NULL;
    unsigned int        sessionAttributes2 = 0;


    if (!key_id) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               ERR_R_PASSED_NULL_PARAMETER);
        return NULL;
    }
    
    // check if the file exists
    if ((bf = BIO_new_file(key_id, "r")) == NULL) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               TPM_R_FILE_NOT_FOUND);
        return NULL;
    }

    tssl = PEM_read_bio_TSSLOADABLE(bf, NULL, NULL, NULL);
    BIO_free(bf);

    
    if (!tssl) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               TPM_R_FILE_READ_FAILED);
        goto load_err;
    }

    if (OBJ_obj2txt(oid, sizeof(oid), tssl->type, 1) == 0) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY, TPM_R_FILE_READ_FAILED);
        goto load_err;
    }

    if (strcmp(OID_loadableKey, oid) == 0) {
        DBG ("TSSL key type is of format that can be loaded in TPM 2.0");
    } else if (strcmp(OID_12Key, oid) == 0) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               TPM_R_TPM_1_2_KEY);
        goto load_err;
    } else if (strcmp(OID_importableKey, oid) == 0) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               TPM_R_KEY_UNSUPPORTED);
        goto load_err;
   } else {
       TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY, TPM_R_KEY_UNRECOGNIZED);
       goto err;
   }

    // since this TPM key was wrapped in the Endorsement
    // Key hierarchy and its handle was persisted, we will
    // specify that as the Parent Handle for the Load operation
    if (!tssl->parent) {
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY, TPM_R_KEY_NO_PARENT_HANDLE);
        goto load_err;
    }

    input.parentHandle = ASN1_INTEGER_get(tssl->parent);
    DBG ("Got parent handle 0x%x", input.parentHandle);
    // unmarshal the public and private key portions from
    // within the TPM ASN1 key blob
    p_tpm2_TPM_PrivateKey_Unmarshal(&input.inPrivate,
                                    &(tssl->privkey->data),
                                    &(tssl->privkey->length));
    p_tpm2_TPM_PublicKey_Unmarshal(&input.inPublic,
                                   &(tssl->pubkey->data),
                                   &(tssl->pubkey->length),
                                   FALSE);
    if ((rc = p_tpm2_TPM_Execute(hContext,
                                 (RESPONSE_PARAMETERS *)&output,
                                 (COMMAND_PARAMETERS *)&input,
                                 NULL,
                                 TPM_CC_Load,
                                 sessionHandle0,
                                 parentPassword,
                                 sessionAttributes0,
                                 sessionHandle1,
                                 NULL,
                                 sessionAttributes1,
                                 sessionHandle2,
                                 NULL,
                                 sessionAttributes2,
                                 TPM_RH_NULL, NULL, 0))) { 
        DBG("Context Load Failed: Ret code %08x", rc);
        TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY,
               TPM_R_REQUEST_FAILED);
        goto load_err;
    }
    hKey = output.objectHandle;

    /* create the new objects to return */
    if ((pkey = EVP_PKEY_new()) == NULL) {
        goto err;
    }
    pkey->type = EVP_PKEY_RSA;

    if ((rsa = RSA_new()) == NULL) {
        EVP_PKEY_free(pkey);
        goto err;
    }
    rsa->meth = &tpm_rsa;
    /* call our local init function here */
    rsa->meth->init(rsa);
    pkey->pkey.rsa = rsa;

    if (!fill_out_rsa_object(rsa, 
                             &input.inPublic.publicArea,
                             hKey)) {
        EVP_PKEY_free(pkey);
        RSA_free(rsa);
        goto err;
    }

    EVP_PKEY_assign_RSA(pkey, rsa);
    return pkey;

err:
    tpm_engine_flush_key_context(hKey);
    hKey = NULL_HKEY;
    TSSerr(TPM_F_TPM_ENGINE_LOAD_KEY, ERR_R_MALLOC_FAILURE);

load_err:
    //TSSLOADABLE_free(tssl);
    return NULL;
}

static int tpm_engine_ctrl(ENGINE * e, int cmd, long i, void *p, void (*f) ())
{
    int initialised = ((tpm_dso == NULL) ? 0 : 1);
    switch (cmd) {
        case TPM_CMD_SO_PATH:
            if (p == NULL) {
                TSSerr(TPM_F_TPM_ENGINE_CTRL,
                       ERR_R_PASSED_NULL_PARAMETER);
                return 0;
            }
            if (initialised) {
                TSSerr(TPM_F_TPM_ENGINE_CTRL,
                       TPM_R_ALREADY_LOADED);
                return 0;
            }
            TPM_LIBNAME = (const char *) p;
            return 1;
        default:
            break;
    }
    TSSerr(TPM_F_TPM_ENGINE_CTRL, TPM_R_CTRL_COMMAND_NOT_IMPLEMENTED);
    return 0;
}

static int tpm_rsa_init(RSA *rsa)
{
    if (ex_app_data == TPM_ENGINE_EX_DATA_UNINIT)
        ex_app_data = RSA_get_ex_new_index(0, NULL, NULL, NULL, NULL);

    if (ex_app_data == TPM_ENGINE_EX_DATA_UNINIT) {
        TSSerr(TPM_F_TPM_RSA_INIT, TPM_R_REQUEST_FAILED);
        return 0;
    }

    return 1;
}

static int tpm_rsa_finish(RSA *rsa)
{
    struct rsa_app_data *app_data = RSA_get_ex_data(rsa, ex_app_data);

    OPENSSL_free(app_data);

    return 1;
}

static int tpm_rsa_priv_dec(int flen,
                const unsigned char *from,
                unsigned char *to,
                RSA *rsa,
                int padding)
{
    struct rsa_app_data *app_data = RSA_get_ex_data(rsa, ex_app_data);
    TPM_RC result;
    UINT32 out_len;
    int rv;
    RSA_Decrypt_In input;
    RSA_Decrypt_Out output;
    // the parent object is not passwod protected
    // but it may be in the future.
    const char          *parentPassword = NULL;
    TPMI_SH_AUTH_SESSION        sessionHandle0 = TPM_RS_PW;
    unsigned int        sessionAttributes0 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle1 = TPM_RH_NULL;
    unsigned int        sessionAttributes1 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle2 = TPM_RH_NULL;
    unsigned int        sessionAttributes2 = 0;


    if (!app_data) {
        TSSerr(TPM_F_TPM_RSA_PRIV_DEC, TPM_R_NO_APP_DATA);
        if ((rv = RSA_PKCS1_SSLeay()->rsa_priv_dec(flen, from, to, rsa,
                        padding)) < 0) {
            TSSerr(TPM_F_TPM_RSA_PRIV_DEC, TPM_R_REQUEST_FAILED);
        }

        return rv;
    }
    
    // hKey is the handle of the private key that is used for decrypt
    if (app_data->hKey == NULL_HKEY) {
        TSSerr(TPM_F_TPM_RSA_PRIV_DEC, TPM_R_INVALID_KEY);
        return 0;
    }
    /* handler of the private key that will perform rsa decrypt */
    input.keyHandle = app_data->hKey;

    // fill in the TPM2RB_PUBLIC_KEY_RSA structure with the
    // cipher text and cipher lenght
    {
        input.label.t.size = 0;
        input.cipherText.t.size = flen;
        memcpy(input.cipherText.t.buffer, from, flen); 
    }

    /* 
     * Table 157 - Definition of {RSA} TPMT_RSA_DECRYPT Structure:
     * we MAY set the input scheme to TPM_ALG_NULL to allow
     * for the encryption algorithm prescribed in the digital 
     * certificate to be used for encryption
     */
    input.inScheme.scheme = TPM_ALG_RSAES; /* TPM_ALG_NULL; */

    // decrypt this cipher text using the private key stored inside
    // tpm and referenced by hKey
    if ((result = p_tpm2_TPM_Execute(hContext,
                                     (RESPONSE_PARAMETERS *)&output,
                                     (COMMAND_PARAMETERS *)&input,
                                     NULL,
                                     TPM_CC_RSA_Decrypt,
                                     sessionHandle0,
                                     parentPassword,
                                     sessionAttributes0,
                                     sessionHandle1,
                                     NULL,
                                     sessionAttributes1,
                                     sessionHandle2,
                                     NULL, 
                                     sessionAttributes2,
                                     TPM_RH_NULL, NULL, 0))) {
        DBG("RSA Decrypt Failed: Ret code %d", result);
        TSSerr(TPM_F_TPM_RSA_PRIV_DEC, TPM_R_REQUEST_FAILED);
        return 0;
    }
    DBG ("Doing RSA Decryption");

    // Unmarshal the output data and return decrypted cipher text
    // and output length
    rv = p_tpm2_Structure_Marshal(&to, &out_len,
                               &output.message,
                               (MarshalFunction_t)
                               TSS_TPM2B_PUBLIC_KEY_RSA_Marshal);
    if (rv == 0) {
        DBG("writing out %d bytes as a signature", out_len);
        return out_len;
    }
    return  0;
}

static int tpm_rsa_priv_enc(int flen,
                const unsigned char *from,
                unsigned char *to,
                RSA *rsa,
                int padding)
{
    struct rsa_app_data *app_data = RSA_get_ex_data(rsa, ex_app_data);
    TPM_RC result = 0;
    UINT32 sig_len;
    int rv;
    RSA_Decrypt_In input;
    RSA_Decrypt_Out output;
    // the parent object is not passwod protected
    // but it may be in the future.
    const char          *parentPassword = NULL;
    TPMI_SH_AUTH_SESSION        sessionHandle0 = TPM_RS_PW;
    unsigned int        sessionAttributes0 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle1 = TPM_RH_NULL;
    unsigned int        sessionAttributes1 = 0;
    TPMI_SH_AUTH_SESSION        sessionHandle2 = TPM_RH_NULL;
    unsigned int        sessionAttributes2 = 0;

    if (!app_data) {
        TSSerr(TPM_F_TPM_RSA_PRIV_DEC, TPM_R_NO_APP_DATA);
        if ((rv = RSA_PKCS1_SSLeay()->rsa_priv_enc(flen, from, to, rsa,
                               padding)) < 0) {
            TSSerr(TPM_F_TPM_RSA_PRIV_ENC, TPM_R_REQUEST_FAILED);
        }
        return rv;
    }

    if (padding != RSA_PKCS1_PADDING) {
        TSSerr(TPM_F_TPM_RSA_PRIV_ENC, TPM_R_INVALID_PADDING_TYPE);
        return 0;
    }

    // hKey is the handle to the private key that is used for hashing
    if (app_data->hKey == NULL_HKEY) {
        TSSerr(TPM_F_TPM_RSA_PRIV_ENC, TPM_R_INVALID_KEY);
        return 0;
    }
    /* handler of the private key that will perform signing */
    input.keyHandle = app_data->hKey;

    /* 
     * Table 145 - Definition of TPMT_SIG_SCHEME inscheme:
     * we will set the input scheme to TPM_ALG_NULL to allow
     * for the hash algorithm prescribed in the digital certificate
     * to be used for signing.
     *
     * Note that we are using a Decryption operation instead of ]
     * a TPM 2.0 Sign operation because of a serious limitation in the
     * IBM TSS that it will only sign digests which it has hashed itself,
     * i.e. the hash has a corresponding TPM_ST_HASHCHECK validation
     * ticket in TPM memory. Long story short, TPM will only sign
     * stuff it knows the OID to.
     *
     * We will therefore specify a Decyrption operation with our
     * own padding applied upto the RSA block size and specify
     * a TPM_ALG_NULL hashing scheme so that a decrypt operation
     * essentially becomes an encrypt op
     */
    input.inScheme.scheme = TPM_ALG_NULL;
    
    /* digest to be signed */
    int size = RSA_size(rsa);
    input.cipherText.t.size = size;
    RSA_padding_add_PKCS1_type_1(input.cipherText.t.buffer, 
                                 size, from, flen);
    input.label.t.size = 0;

    // sign this digest using the private key stored inside
    // tpm and referenced by hKey
    if ((result = p_tpm2_TPM_Execute(hContext,
                                     (RESPONSE_PARAMETERS *)&output,
                                     (COMMAND_PARAMETERS *)&input,
                                     NULL,
                                     TPM_CC_RSA_Decrypt,
                                     sessionHandle0,
                                     parentPassword,
                                     sessionAttributes0,
                                     sessionHandle1,
                                     NULL,
                                     sessionAttributes1,
                                     sessionHandle2,
                                     NULL, 
                                     sessionAttributes2,
                                     TPM_RH_NULL, NULL, 0))) {
        DBG("RSA Sign Failed: Ret code %d", result);
        TSSerr(TPM_F_TPM_RSA_PRIV_ENC, TPM_R_REQUEST_FAILED);
        return 0;
    }

    // thats right son!!! finally signed
    sig_len = output.message.t.size;
    memcpy(to, output.message.t.buffer, sig_len);

    DBG("writing out %d bytes as a signature", sig_len);
    return sig_len;
}

/* This stuff is needed if this ENGINE is being compiled into a self-contained
 * shared-library. */
static int bind_fn(ENGINE * e, const char *id)
{
    if (id && (strcmp(id, engine_tpm_id) != 0)) {
        TSSerr(TPM_F_TPM_BIND_FN, TPM_R_ID_INVALID);
        return 0;
    }
    if (!bind_helper(e)) {
        TSSerr(TPM_F_TPM_BIND_FN, TPM_R_REQUEST_FAILED);
        return 0;
    }
    return 1;
}

IMPLEMENT_DYNAMIC_CHECK_FN()
IMPLEMENT_DYNAMIC_BIND_FN(bind_fn)
