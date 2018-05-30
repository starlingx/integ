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

#include <openssl/err.h>
#include <openssl/dso.h>
#include <openssl/engine.h>

#include "e_tpm2.h"

/* BEGIN ERROR CODES */
#ifndef OPENSSL_NO_ERR
static ERR_STRING_DATA TPM_str_functs[] = {
    {ERR_PACK(0, TPM_F_TPM_ENGINE_CTRL, 0), "TPM_ENGINE_CTRL"},
    {ERR_PACK(0, TPM_F_TPM_ENGINE_FINISH, 0), "TPM_ENGINE_FINISH"},
    {ERR_PACK(0, TPM_F_TPM_ENGINE_INIT, 0), "TPM_ENGINE_INIT"},
    {ERR_PACK(0, TPM_F_TPM_RSA_PRIV_ENC, 0), "TPM_RSA_PRIV_ENC"},
    {ERR_PACK(0, TPM_F_TPM_RSA_PRIV_DEC, 0), "TPM_RSA_PRIV_DEC"},
    {ERR_PACK(0, TPM_F_TPM_RSA_FINISH, 0), "TPM_RSA_FINISH"},
    {ERR_PACK(0, TPM_F_TPM_RSA_INIT, 0), "TPM_RSA_INIT"},
    {ERR_PACK(0, TPM_F_TPM_ENGINE_LOAD_KEY, 0), "TPM_ENGINE_LOAD_KEY"},
    {ERR_PACK(0, TPM_F_TPM_BIND_FN, 0), "TPM_BIND_FN"},
    {ERR_PACK(0, TPM_F_TPM_FILL_RSA_OBJECT, 0), "TPM_FILL_RSA_OBJECT"},
    {ERR_PACK(0, TPM_F_TPM_FLUSH_OBJECT_CONTEXT, 0), "TPM_FLUSH_OBJECT_CONTEXT"},
    {0, NULL}
};

static ERR_STRING_DATA TPM_str_reasons[] = {
    {TPM_R_ALREADY_LOADED, "already loaded"},
    {TPM_R_CTRL_COMMAND_NOT_IMPLEMENTED, "ctrl command not implemented"},
    {TPM_R_DSO_FAILURE, "dso failure"},
    {TPM_R_MISSING_KEY_COMPONENTS, "missing key components"},
    {TPM_R_NOT_INITIALISED, "not initialised"},
    {TPM_R_NOT_LOADED, "not loaded"},
    {TPM_R_OPERANDS_TOO_LARGE, "operands too large"},
    {TPM_R_OUTLEN_TO_LARGE, "outlen to large"},
    {TPM_R_REQUEST_FAILED, "request failed"},
    {TPM_R_REQUEST_TOO_BIG, "requested number of random bytes > 4096"},
    {TPM_R_UNDERFLOW_CONDITION, "underflow condition"},
    {TPM_R_UNDERFLOW_KEYRECORD, "underflow keyrecord"},
    {TPM_R_UNIT_FAILURE, "unit failure"},
    {TPM_R_INVALID_KEY_SIZE, "invalid key size"},
    {TPM_R_BN_CONVERSION_FAILED, "bn conversion failed"},
    {TPM_R_INVALID_EXPONENT, "invalid exponent"},
    {TPM_R_NO_APP_DATA, "no app data in RSA object"},
    {TPM_R_INVALID_ENC_SCHEME, "invalid encryption scheme"},
    {TPM_R_INVALID_MSG_SIZE, "invalid message size to sign"},
    {TPM_R_INVALID_PADDING_TYPE, "invalid padding type"},
    {TPM_R_INVALID_KEY, "invalid key"},
    {TPM_R_FILE_NOT_FOUND, "file to load not found"},
    {TPM_R_FILE_READ_FAILED, "failed reading the key file"},
    {TPM_R_ID_INVALID, "engine id doesn't match"},
    {TPM_R_TPM_1_2_KEY, "tpm 1.2 key format not supported"},
    {TPM_R_KEY_UNSUPPORTED, "unsupported TPM key format"},
    {TPM_R_KEY_UNRECOGNIZED, "unrecognized TPM key format"},
    {TPM_R_KEY_NO_PARENT_HANDLE, "TPM key has no parent handle"},
    {0, NULL}
};

#endif

static ERR_STRING_DATA TPM_lib_name[] = {
    {0, TPM_LIB_NAME},
    {0, NULL}
};


static int TPM_lib_error_code = 0;
static int TPM_error_init = 1;

void ERR_load_TPM_strings(void)
{
    if (TPM_lib_error_code == 0) {
        TPM_lib_error_code = ERR_get_next_error_library();
        DBG("TPM_lib_error_code is %d", TPM_lib_error_code);
    }

    if (TPM_error_init) {
        TPM_error_init = 0;
#ifndef OPENSSL_NO_ERR
        ERR_load_strings(TPM_lib_error_code, TPM_str_functs);
        ERR_load_strings(TPM_lib_error_code, TPM_str_reasons);
#endif
        TPM_lib_name[0].error = ERR_PACK(TPM_lib_error_code, 0, 0);
        ERR_load_strings(0, TPM_lib_name);
    }
}

void ERR_unload_TPM_strings(void)
{
    if (TPM_error_init == 0) {
#ifndef OPENSSL_NO_ERR
        ERR_unload_strings(TPM_lib_error_code, TPM_str_functs);
        ERR_unload_strings(TPM_lib_error_code, TPM_str_reasons);
#endif

        ERR_load_strings(0, TPM_lib_name);
        TPM_error_init = 1;
    }
}

void ERR_TSS_error(int function, int reason, char *file, int line)
{
    if (TPM_lib_error_code == 0)
        TPM_lib_error_code = ERR_get_next_error_library();

    ERR_PUT_error(TPM_lib_error_code, function, reason, file, line);
}

