#!/bin/bash

tr -d " \n" | sed -e "s/|/\n\t| /g" -e "s/&/ & /g" -e "s/notR=/\nnotR =\n\t  /" -e "s/#/# /" -e '$a\'
