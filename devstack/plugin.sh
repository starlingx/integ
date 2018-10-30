#!/bin/bash

# ``stack.sh`` calls the entry points in this order:
#
echo_summary "integ devstack plugin.sh called: $1/$2"

# check for service enabled
if is_service_enabled stx-integ; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of source
        echo_summary "Install stx-integ"
        install_integ
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configure stx-integ"
        configure_integ
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the service
        echo_summary "Initialize and start stx-integ"
        init_integ
    elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
        # do sanity test
        echo_summary "do test-config"
    fi

    if [[ "$1" == "unstack" ]]; then
        # Shut down services
        echo_summary "Stop stx-integ services"
        stop_integ
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Clean stx-update"
        cleanup_integ
    fi
fi
