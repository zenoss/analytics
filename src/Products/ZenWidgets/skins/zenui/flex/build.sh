#!/bin/sh
echo "Building ZenNetMap.swf"
mxmlc -library-path+="comfolderfoundinbranch/springGraph" --static-link-runtime-shared-libraries=true  --show-actionscript-warnings=true --strict=true -file-specs ZenNetMap.mxml
