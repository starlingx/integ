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

#ifndef _E_TPM_H
#define _E_TPM_H

#include <tss2/tss.h>
#include <tss2/tssutils.h>
#include <tss2/tssresponsecode.h>
#include <tss2/Unmarshal_fp.h>
#include <tss2/tssmarshal.h>
#include <tss2/tsscryptoh.h>

#define TPM_LIB_NAME "tpm2 engine"

#define NULL_HCONTEXT   NULL
#define NULL_HKEY   0

void ERR_load_TPM_strings(void);
void ERR_unload_TPM_strings(void);
void ERR_TSS_error(int function, int reason, char *file, int line);

#define TSSerr(f,r) ERR_TSS_error((f),(r),__FILE__,__LINE__)
#define DBG(x, ...) fprintf(stderr, "DEBUG %s:%d %s " x "\n", __FILE__,__LINE__,__FUNCTION__,##__VA_ARGS__)

/* Error codes for the TPM functions. */

/* Function codes. */
#define TPM_F_TPM_ENGINE_CTRL           100
#define TPM_F_TPM_ENGINE_FINISH         101
#define TPM_F_TPM_ENGINE_INIT           102
#define TPM_F_TPM_RSA_PRIV_ENC          103
#define TPM_F_TPM_RSA_PRIV_DEC          104
#define TPM_F_TPM_RSA_FINISH            105
#define TPM_F_TPM_RSA_INIT              106
#define TPM_F_TPM_ENGINE_LOAD_KEY       107
#define TPM_F_TPM_BIND_FN               108
#define TPM_F_TPM_FILL_RSA_OBJECT       109
#define TPM_F_TPM_FLUSH_OBJECT_CONTEXT  110

/* Reason codes. */
#define TPM_R_ALREADY_LOADED            100
#define TPM_R_CTRL_COMMAND_NOT_IMPLEMENTED  101
#define TPM_R_DSO_FAILURE               102
#define TPM_R_MEXP_LENGTH_TO_LARGE      103
#define TPM_R_MISSING_KEY_COMPONENTS    104
#define TPM_R_NOT_INITIALISED           105
#define TPM_R_NOT_LOADED                106
#define TPM_R_OPERANDS_TOO_LARGE        107
#define TPM_R_OUTLEN_TO_LARGE           108
#define TPM_R_REQUEST_FAILED            109
#define TPM_R_UNDERFLOW_CONDITION       110
#define TPM_R_UNDERFLOW_KEYRECORD       111
#define TPM_R_UNIT_FAILURE              112
#define TPM_R_INVALID_KEY_SIZE          113
#define TPM_R_BN_CONVERSION_FAILED      114
#define TPM_R_INVALID_EXPONENT          115
#define TPM_R_REQUEST_TOO_BIG           116
#define TPM_R_NO_APP_DATA               117
#define TPM_R_INVALID_ENC_SCHEME        118
#define TPM_R_INVALID_MSG_SIZE          119
#define TPM_R_INVALID_PADDING_TYPE      120
#define TPM_R_INVALID_KEY               121
#define TPM_R_FILE_NOT_FOUND            122
#define TPM_R_FILE_READ_FAILED          123
#define TPM_R_ID_INVALID                124
#define TPM_R_TPM_1_2_KEY               125
#define TPM_R_KEY_UNSUPPORTED           126
#define TPM_R_KEY_UNRECOGNIZED          127
#define TPM_R_KEY_NO_PARENT_HANDLE      128

/* structure pointed to by the RSA object's app_data pointer.
 * this is used to tag TPM meta data in the RSA object and
 * use that to distinguish between a vanilla Openssl RSA object
 * and a TPM RSA object  
 */ 
struct rsa_app_data
{
    TPMI_DH_OBJECT hKey;
    // add additional meta data as need be
};

#define TPM_ENGINE_EX_DATA_UNINIT       -1
#define RSA_PKCS1_OAEP_PADDING_SIZE     (2 * SHA_DIGEST_LENGTH + 2)

#endif
