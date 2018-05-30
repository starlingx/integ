/*
 * Copyright (c) 2017 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */
/* ====================================================================
 * 
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
#include <getopt.h>
#include <string.h>
#include <strings.h>
#include <errno.h>

#include <openssl/rsa.h>
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#include <tss2/tss.h>
#include <tss2/tssutils.h>
#include <tss2/tssmarshal.h>
#include <tss2/tssresponsecode.h>

#include "tpm2-asn.h"

static struct option long_options[] = {
   {"auth", 0, 0, 'a'},
   {"help", 0, 0, 'h'},
   {"name-scheme", 1, 0, 'n'},
   {"parent-handle", 1, 0, 'p'},
   {"wrap", 1, 0, 'w'},
   {0, 0, 0, 0}
};

static TPM_ALG_ID name_alg = TPM_ALG_SHA256;
static int name_alg_size = SHA256_DIGEST_SIZE;

void
usage(char *argv0)
{
   fprintf(stderr, "\t%s: create a TPM key and write it to disk\n"
       "\tusage: %s [options] <filename>\n\n"
       "\tOptions:\n"
       "\t\t-a|--auth          require a password for the key [NO]\n"
       "\t\t-h|--help          print this help message\n"
       "\t\t-n|--name-scheme   name algorithm to use sha1 [sha256] sha384 sha512\n"
       "\t\t-p|--parent-handle persistent handle of parent key\n"
       "\t\t-w|--wrap [file]   wrap an existing openssl PEM key\n",
       argv0, argv0);
   exit(-1);
}

void tpm2_error(TPM_RC rc, const char *reason)
{
   const char *msg, *submsg, *num;

   fprintf(stderr, "%s failed with %d\n", reason, rc);
   TSS_ResponseCode_toString(&msg, &submsg, &num, rc);
   fprintf(stderr, "%s%s%s\n", msg, submsg, num);
}

void
openssl_print_errors()
{
   ERR_load_ERR_strings();
   ERR_load_crypto_strings();
   ERR_print_errors_fp(stderr);
}

int
openssl_write_tpmfile(const char *file, BYTE *pubkey, int pubkey_len,
             BYTE *privkey, int privkey_len, int empty_auth,
             TPM_HANDLE parent)
{
   TSSLOADABLE tssl;
   BIO *outb;

   /* clear structure so as not to have to set optional parameters */
   memset(&tssl, 0, sizeof(tssl));
   if ((outb = BIO_new_file(file, "w")) == NULL) {
                fprintf(stderr, "Error opening file for write: %s\n", file);
       return 1;
   }
   tssl.type = OBJ_txt2obj(OID_loadableKey, 1);
   tssl.emptyAuth = empty_auth;
   if ((parent & 0xff000000) == 0x81000000) {
       tssl.parent = ASN1_INTEGER_new();
       ASN1_INTEGER_set(tssl.parent, parent);
   }
   tssl.pubkey = ASN1_OCTET_STRING_new();
   ASN1_STRING_set(tssl.pubkey, pubkey, pubkey_len);
   tssl.privkey = ASN1_OCTET_STRING_new();
   ASN1_STRING_set(tssl.privkey, privkey, privkey_len);

   PEM_write_bio_TSSLOADABLE(outb, &tssl);
   BIO_free(outb);
   return 0;
}

EVP_PKEY *
openssl_read_key(char *filename)
{
        BIO *b = NULL;
   EVP_PKEY *pkey;

        b = BIO_new_file(filename, "r");
        if (b == NULL) {
                fprintf(stderr, "Error opening file for read: %s\n", filename);
                return NULL;
        }

        if ((pkey = PEM_read_bio_PrivateKey(b, NULL, PEM_def_callback, NULL)) == NULL) {
                fprintf(stderr, "Reading key %s from disk failed.\n", filename);
                openssl_print_errors();
        }
   BIO_free(b);

        return pkey;
}

void tpm2_public_template_rsa(TPMT_PUBLIC *pub)
{
   pub->type = TPM_ALG_RSA;
   pub->nameAlg = name_alg;
   /* note: all our keys are decrypt only.  This is because
    * we use the TPM2_RSA_Decrypt operation for both signing
    * and decryption (see e_tpm2.c for details) */
   pub->objectAttributes.val = TPMA_OBJECT_NODA |
       TPMA_OBJECT_DECRYPT |
       TPMA_OBJECT_SIGN |
       TPMA_OBJECT_USERWITHAUTH;
   pub->authPolicy.t.size = 0;
   pub->parameters.rsaDetail.symmetric.algorithm = TPM_ALG_NULL;
   pub->parameters.rsaDetail.scheme.scheme = TPM_ALG_NULL;
}

TPM_RC openssl_to_tpm_public_rsa(TPMT_PUBLIC *pub, EVP_PKEY *pkey)
{
   RSA *rsa = EVP_PKEY_get1_RSA(pkey);
   BIGNUM *n, *e;
   int size = RSA_size(rsa);
   unsigned long exp;

   if (size > MAX_RSA_KEY_BYTES)
       return TPM_RC_KEY_SIZE;

#if OPENSSL_VERSION_NUMBER < 0x10100000
   n = rsa->n;
   e = rsa->e;
#else
   RSA_get0_key(&n, &e, NULL);
#endif
   exp = BN_get_word(e);
   /* TPM limitations means exponents must be under a word in size */
   if (exp == 0xffffffffL)
       return TPM_RC_KEY_SIZE;
   tpm2_public_template_rsa(pub);
   pub->parameters.rsaDetail.keyBits = size*8;
   if (exp == 0x10001)
       pub->parameters.rsaDetail.exponent = 0;
   else
       pub->parameters.rsaDetail.exponent = exp;

   pub->unique.rsa.t.size = BN_bn2bin(n, pub->unique.rsa.t.buffer);

   return 0;
}

TPM_RC openssl_to_tpm_public(TPM2B_PUBLIC *pub, EVP_PKEY *pkey)
{
   TPMT_PUBLIC *tpub = &pub->publicArea;
   pub->size = sizeof(*pub);

   switch (EVP_PKEY_type(pkey->type)) {
   case EVP_PKEY_RSA:
       return openssl_to_tpm_public_rsa(tpub, pkey);
   default:
       break;
   }
   return TPM_RC_ASYMMETRIC;
}

TPM_RC openssl_to_tpm_private_rsa(TPMT_SENSITIVE *s, EVP_PKEY *pkey)
{
   BIGNUM *q;
   TPM2B_PRIVATE_KEY_RSA *t2brsa = &s->sensitive.rsa;
   RSA *rsa = EVP_PKEY_get1_RSA(pkey);

#if OPENSSL_VERSION_NUMBER < 0x10100000
   q = rsa->q;
#else
   BIGNUM *p;

   RSA_get0_factors(rsa, &p, &q);
#endif

   if (!q)
       return TPM_RC_ASYMMETRIC;

   s->sensitiveType = TPM_ALG_RSA;
   s->seedValue.b.size = 0;

   t2brsa->t.size = BN_bn2bin(q, t2brsa->t.buffer);
   return 0;
}

TPM_RC openssl_to_tpm_private(TPMT_SENSITIVE *priv, EVP_PKEY *pkey)
{
   switch (EVP_PKEY_type(pkey->type)) {
   case EVP_PKEY_RSA:
       return openssl_to_tpm_private_rsa(priv, pkey);
   default:
       break;
   }
   return TPM_RC_ASYMMETRIC;
}

TPM_RC wrap_key(TPM2B_PRIVATE *priv, const char *password, EVP_PKEY *pkey)
{
   TPMT_SENSITIVE s;
   TPM2B_SENSITIVE b;
   BYTE *buf;
   int32_t size;
   TPM_RC rc;

   memset(&b, 0, sizeof(b));
   memset(&s, 0, sizeof(s));

   openssl_to_tpm_private(&s, pkey);

   if (password) {
       int len = strlen(password);

       memcpy(s.authValue.b.buffer, password, len);
       s.authValue.b.size = len;
   } else {
       s.authValue.b.size = 0;
   }
   size = sizeof(s);
   buf = b.b.buffer;
   rc = TSS_TPMT_SENSITIVE_Marshal(&s, &b.b.size, &buf, &size);
   if (rc)
       tpm2_error(rc, "TSS_TPMT_SENSITIVE_Marshal");

   size = sizeof(*priv);
   buf = priv->b.buffer;
   priv->b.size = 0;
   /* no encryption means innerIntegrity and outerIntegrity are
   * absent, so the TPM2B_PRIVATE is a TPMT_SENSITIVE*/
   rc = TSS_TPM2B_PRIVATE_Marshal((TPM2B_PRIVATE *)&b, &priv->b.size, &buf, &size);
   if (rc)
       tpm2_error(rc, "TSS_TPM2B_PRIVATE_Marshal");

   return TPM_RC_ASYMMETRIC;
}

int main(int argc, char **argv)
{
   char *filename, c, *wrap = NULL, *auth = NULL;
   int option_index;
   const char *reason;
   TSS_CONTEXT *tssContext = NULL;
   TPM_HANDLE parent = 0;
   TPM_RC rc = 0;
   BYTE pubkey[sizeof(TPM2B_PUBLIC)],privkey[sizeof(TPM2B_PRIVATE)], *buffer;
   uint16_t pubkey_len, privkey_len;
   int32_t size = 0;
   TPM2B_PUBLIC *pub;
   TPM2B_PRIVATE *priv;


   while (1) {
       option_index = 0;
       c = getopt_long(argc, argv, "n:ap:hw:",
               long_options, &option_index);
       if (c == -1)
           break;

       switch (c) {
           case 'a':
               auth = malloc(128);
               break;
           case 'h':
               usage(argv[0]);
               break;
           case 'n':
               if (!strcasecmp("sha1", optarg)) {
                   name_alg = TPM_ALG_SHA1;
                   name_alg_size = SHA1_DIGEST_SIZE;
               } else if (strcasecmp("sha256", optarg)) {
                   /* default, do nothing */
               } else if (strcasecmp("sha384", optarg)) {
                   name_alg = TPM_ALG_SHA384;
                   name_alg_size = SHA384_DIGEST_SIZE;
#ifdef TPM_ALG_SHA512
               } else if (strcasecmp("sha512", optarg)) {
                   name_alg = TPM_ALG_SHA512;
                   name_alg_size = SHA512_DIGEST_SIZE;
#endif
               } else {
                   usage(argv[0]);
               }
               break;
           case 'p':
               parent = strtol(optarg, NULL, 16);
               break;
           case 'w':
               wrap = optarg;
               break;
           default:
               usage(argv[0]);
               break;
       }
   }

   filename = argv[argc - 1];

   if (argc < 2)
       usage(argv[0]);

   if (!wrap) {
       fprintf(stderr, "wrap is a compulsory option\n");
       usage(argv[0]);  
   }

   if (!parent) {
       fprintf(stderr, "parent handle is a compulsory option\n");
       usage(argv[0]);
   }

   if (parent && (parent & 0xff000000) != 0x81000000) {
       fprintf(stderr, "you must specify a persistent parent handle\n");
       usage(argv[0]);
   }

   if (auth) {
       if (EVP_read_pw_string(auth, 128, "Enter TPM key authority: ", 1)) {
           fprintf(stderr, "Passwords do not match\n");
           exit(1);
       }
   }

   rc = TSS_Create(&tssContext);
   if (rc) {
       reason = "TSS_Create";
       goto out_err;
   }

   /* 
    * avoid using the device TCTI as that will bind
    * exclusively to the TPM device. Instead
    * use the Kernel TPM Resource Manager as that
    * allows concurrent access
    *
    * N.B: This assumes that the kernel-modules-tpm
    * pkg is installed with the modified tpm_crb KLM
    */
   rc = TSS_SetProperty(tssContext, TPM_DEVICE, "/dev/tpmrm0");
   if (rc) {
        reason = "TSS_SetProperty: TPM_USE_RESOURCE_MANAGER";
        goto out_err;
   }

   if (wrap) {
       Import_In iin;
       Import_Out iout;
       EVP_PKEY *pkey;

       /* may be needed to decrypt the key */
       OpenSSL_add_all_ciphers();
       pkey = openssl_read_key(wrap);
       if (!pkey) {
           reason = "unable to read key";
           goto out_delete;
       }

       iin.parentHandle = parent;
       iin.encryptionKey.t.size = 0;
       openssl_to_tpm_public(&iin.objectPublic, pkey);
       /* set random iin.symSeed */
       iin.inSymSeed.t.size = 0;
       iin.symmetricAlg.algorithm = TPM_ALG_NULL;
       wrap_key(&iin.duplicate, auth, pkey);
       openssl_to_tpm_public(&iin.objectPublic, pkey);
       rc = TSS_Execute(tssContext,
                (RESPONSE_PARAMETERS *)&iout,
                (COMMAND_PARAMETERS *)&iin,
                NULL,
                TPM_CC_Import,
                TPM_RS_PW, NULL, 0,
                TPM_RH_NULL, NULL, 0,
                TPM_RH_NULL, NULL, 0,
                TPM_RH_NULL, NULL, 0);
       if (rc) {
           reason = "TPM2_Import";
           goto out_flush;
       }
       pub = &iin.objectPublic;
       priv = &iout.outPrivate;
   }

   buffer = pubkey;
   pubkey_len = 0;
   size = sizeof(pubkey);
   TSS_TPM2B_PUBLIC_Marshal(pub, &pubkey_len, &buffer, &size);
   buffer = privkey;
   privkey_len = 0;
   size = sizeof(privkey);
   TSS_TPM2B_PRIVATE_Marshal(priv, &privkey_len, &buffer, &size);
   openssl_write_tpmfile(filename, pubkey, pubkey_len, privkey, privkey_len, auth == NULL, parent);
   TSS_Delete(tssContext);
   exit(0);

 out_flush:
 out_delete:
   TSS_Delete(tssContext);
 out_err:
   tpm2_error(rc, reason);

   exit(1);
}
