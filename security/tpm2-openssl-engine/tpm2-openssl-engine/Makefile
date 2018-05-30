#
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

#### Installation options
ENGINEDIR=
UTILDIR=

#### Toolchain options
CC = gcc
LD = $(CC)

#### Debug flags (typically "-g").
# Those flags only feed CFLAGS so it is not mandatory to use this form.
DEBUG_CFLAGS = -g -O2 -Werror -Wno-unused-parameter -Wno-missing-braces

#### Compiler-specific flags that may be used to disable some negative over-
# optimization or to silence some warnings. -fno-strict-aliasing is needed with
# gcc >= 4.4.
SPEC_CFLAGS = -fno-strict-aliasing

#### Common CFLAGS
CFLAGS = $(DEBUG_CFLAGS) $(SPEC_CFLAGS)

#### Common LDFLAGS
LDFLAGS = -g

DYNAMIC_ENGINE=libtpm2.so
UTIL=create_tpm2_key

INCLUDES+=-I${SYSTEM_DIR}/usr/include/
LDFLAGS +=-lcrypto -lc -ltss
SRCS += e_tpm2.c e_tpm2_err.c
HEADERS += e_tpm2.h

OBJS = $(SRCS:.c=.o)

all: $(DYNAMIC_ENGINE) ${UTIL}

${UTIL}: $(OBJS)
	$(CC) -Wall ${CFLAGS} ${INCLUDES} create_tpm2_key.c ${LDFLAGS} -o ${UTIL}

$(DYNAMIC_ENGINE): $(OBJS)
	$(CC) -Wall ${CFLAGS} ${INCLUDES} ${LDFLAGS} -fPIC -c ${SRCS}
	$(CC) -shared -Wl,-soname,${DYNAMIC_ENGINE} ${LDFLAGS} -o ${DYNAMIC_ENGINE} $(OBJS)

install: all
	install -D -m 755 ${DYNAMIC_ENGINE} ${ENGINEDIR}/${DYNAMIC_ENGINE}
	install -D -m 755 ${UTIL} ${UTILDIR}/${UTIL}

clean:
	$(RM) *.o *.so *.so.0
