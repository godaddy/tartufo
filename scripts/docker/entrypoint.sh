#!/bin/sh -e

if [ -n "${SSH_PASS}" ]; then 
    export DISPLAY=:0
    export SSH_ASKPASS="/ssh-askpass.sh"
fi

if [ -f "/tmp/id_rsa" ]; then
    eval "$(ssh-agent -s)"
    ssh-add /tmp/id_rsa
fi

tartufo "$@"
