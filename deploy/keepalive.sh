#!/bin/bash

# Keep database alive to stop it from timing out in 7 days.
# In future, we should source credentials from vault.
sql /nolog << EOF
show tns
connect $ECUMENE_USER/$ECUMENE_PASSWORD@ecumene_high
select current_timestamp from dual;
EOF