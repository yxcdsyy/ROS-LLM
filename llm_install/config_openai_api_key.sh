#!/bin/bash
# -*- coding: utf-8 -*-
# flake8: noqa
#
# Copyright 2023 Herman Ye @Auromix
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Description:
# This script will add your OpenAI-compatible API settings to your .bashrc file.
# It supports Qwen / DashScope compatible mode.
#
# Author: Herman Ye @Auromix
# Modified for OpenAI-compatible services

set -e

echo "This script will add your OpenAI-compatible API settings to your ~/.bashrc file."
echo ""

DEFAULT_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL="qwen-plus-2025-07-28"

read -rp "Enter your API key: " API_KEY
read -rp "Enter your API base URL [default: ${DEFAULT_API_BASE}]: " API_BASE
read -rp "Enter your model name [default: ${DEFAULT_MODEL}]: " MODEL_NAME

API_BASE=${API_BASE:-$DEFAULT_API_BASE}
MODEL_NAME=${MODEL_NAME:-$DEFAULT_MODEL}

BASHRC_FILE="$HOME/.bashrc"

echo ""
echo "The following settings will be written:"
echo "  OPENAI_API_KEY=${API_KEY}"
echo "  OPENAI_API_BASE=${API_BASE}"
echo "  OPENAI_MODEL=${MODEL_NAME}"
echo ""

read -rp "Continue? (y/n) " confirm_initial
if [[ ! "$confirm_initial" =~ ^[Yy]$ ]]; then
  echo "No changes were made."
  exit 0
fi

remove_existing_config() {
  sed -i '/export OPENAI_API_KEY=/d' "$BASHRC_FILE"
  sed -i '/export OPENAI_API_BASE=/d' "$BASHRC_FILE"
  sed -i '/export OPENAI_MODEL=/d' "$BASHRC_FILE"
}

append_new_config() {
  {
    echo ""
    echo "# OpenAI-compatible API configuration for ROS-LLM"
    echo "export OPENAI_API_KEY=\"${API_KEY}\""
    echo "export OPENAI_API_BASE=\"${API_BASE}\""
    echo "export OPENAI_MODEL=\"${MODEL_NAME}\""
  } >> "$BASHRC_FILE"
}

HAS_KEY=0
HAS_BASE=0
HAS_MODEL=0

grep -q 'export OPENAI_API_KEY=' "$BASHRC_FILE" && HAS_KEY=1
grep -q 'export OPENAI_API_BASE=' "$BASHRC_FILE" && HAS_BASE=1
grep -q 'export OPENAI_MODEL=' "$BASHRC_FILE" && HAS_MODEL=1

if [[ $HAS_KEY -eq 1 || $HAS_BASE -eq 1 || $HAS_MODEL -eq 1 ]]; then
  echo "Existing OpenAI-compatible environment variables were found in ${BASHRC_FILE}."
  read -rp "Are you sure you want to replace them? (y/n) " confirm_replace
  if [[ "$confirm_replace" =~ ^[Yy]$ ]]; then
    remove_existing_config
    append_new_config
    echo "Existing configuration was replaced."
  else
    echo "No changes were made."
    exit 0
  fi
else
  append_new_config
  echo "Configuration was added."
fi

# Load settings for current shell session
export OPENAI_API_KEY="${API_KEY}"
export OPENAI_API_BASE="${API_BASE}"
export OPENAI_MODEL="${MODEL_NAME}"

echo ""
echo "Configuration complete."
echo "Current session has been updated with:"
echo "  OPENAI_API_KEY=${OPENAI_API_KEY}"
echo "  OPENAI_API_BASE=${OPENAI_API_BASE}"
echo "  OPENAI_MODEL=${OPENAI_MODEL}"
echo ""
echo "To apply these settings in a new terminal, run:"
echo "  source ~/.bashrc"
echo ""

read -n 1 -r -p "Press any key to exit..."
echo ""
exit 0