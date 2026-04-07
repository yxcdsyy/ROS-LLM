#!/usr/bin/env python3
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
# Author: Herman Ye @Auromix

import json
import os
import site
import sys
import time

# ROS 2 Foxy typically exports PYTHONNOUSERSITE=1.
# Append user site-packages explicitly so pip --user installs remain importable.
user_site_packages = site.getusersitepackages()
if user_site_packages and user_site_packages not in sys.path:
    sys.path.append(user_site_packages)

from openai import OpenAI
import rclpy
from rclpy.node import Node
from llm_interfaces.srv import ChatGPT
from std_msgs.msg import String

from llm_config.user_config import UserConfig


config = UserConfig()


class ChatGPTNode(Node):
    def __init__(self):
        super().__init__("ChatGPT_node")

        self.initialization_publisher = self.create_publisher(
            String, "/llm_initialization_state", 10
        )
        self.llm_state_publisher = self.create_publisher(String, "/llm_state", 10)
        self.llm_state_subscriber = self.create_subscription(
            String, "/llm_state", self.state_listener_callback, 10
        )
        self.llm_input_subscriber = self.create_subscription(
            String, "/llm_input_audio_to_text", self.llm_callback, 10
        )
        self.llm_response_type_publisher = self.create_publisher(
            String, "/llm_response_type", 10
        )
        self.llm_feedback_publisher = self.create_publisher(
            String, "/llm_feedback_to_user", 10
        )
        self.output_publisher = self.create_publisher(String, "ChatGPT_text_output", 10)

        self.function_call_client = self.create_client(
            ChatGPT, "/ChatGPT_function_call_service"
        )

        self.openai_api_key = os.getenv("OPENAI_API_KEY", config.openai_api_key or "")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", "")
        self.openai_model = os.getenv("OPENAI_MODEL", config.openai_model)

        self.openai_client = None
        if not self.openai_api_key:
            self.get_logger().error(
                "OPENAI_API_KEY is empty. Please export OPENAI_API_KEY first."
            )
        else:
            client_kwargs = {"api_key": self.openai_api_key}
            if self.openai_api_base:
                client_kwargs["base_url"] = self.openai_api_base
            self.openai_client = OpenAI(**client_kwargs)
            self.get_logger().info(
                f"LLM client ready. model={self.openai_model}, base_url={self.openai_api_base or 'default'}"
            )

        self.robot_tools = self.convert_functions_to_tools(config.robot_functions_list)

        self.chat_history = list(config.chat_history)
        history_dir = config.chat_history_path
        if not os.path.isdir(history_dir) or not os.access(history_dir, os.W_OK):
            history_dir = "/tmp"
        self.start_timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        self.chat_history_file = os.path.join(
            history_dir, f"chat_history_{self.start_timestamp}.json"
        )
        self.write_chat_history_to_json()

        self.publish_string("llm_model_processing", self.initialization_publisher)

    def state_listener_callback(self, msg):
        self.get_logger().debug(f"model node get current State: {msg.data}")

    def publish_string(self, string_to_send, publisher_to_use):
        msg = String()
        msg.data = "" if string_to_send is None else str(string_to_send)
        publisher_to_use.publish(msg)
        self.get_logger().info(
            f"Topic: {publisher_to_use.topic_name}\nMessage published: {msg.data}"
        )

    def write_chat_history_to_json(self):
        try:
            json_data = json.dumps(self.chat_history, ensure_ascii=False)
            with open(self.chat_history_file, "w", encoding="utf-8") as file:
                file.write(json_data)
            return True
        except IOError as error:
            self.get_logger().error(f"Error writing chat history to JSON: {error}")
            return False

    def add_message_to_history(self, message):
        self.chat_history.append(message)
        if len(self.chat_history) > config.chat_history_max_length:
            # keep the first message (system prompt) when truncating history
            self.chat_history.pop(1 if len(self.chat_history) > 1 else 0)

    def convert_functions_to_tools(self, function_specs):
        tools = []
        seen_names = set()
        for spec in function_specs:
            if not isinstance(spec, dict):
                continue
            function_name = spec.get("name", "")
            if not function_name or function_name in seen_names:
                continue
            seen_names.add(function_name)
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "description": spec.get("description", ""),
                        "parameters": spec.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )
        return tools

    def generate_chatgpt_response(self, enable_tools=True):
        if self.openai_client is None:
            raise RuntimeError("OPENAI client is not initialized.")

        request_kwargs = {
            "model": self.openai_model,
            "messages": self.chat_history,
        }
        if enable_tools and self.robot_tools:
            request_kwargs["tools"] = self.robot_tools
            request_kwargs["tool_choice"] = "auto"

        return self.openai_client.chat.completions.create(**request_kwargs)

    def extract_text_content(self, content):
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return str(content)

    def tool_call_to_history_message(self, assistant_message):
        tool_calls = []
        for index, tool_call in enumerate(assistant_message.tool_calls):
            tool_call_id = tool_call.id or f"tool_call_{index}"
            tool_calls.append(
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments or "{}",
                    },
                }
            )
        return {"role": "assistant", "content": None, "tool_calls": tool_calls}

    def call_robot_function_service(self, function_name, arguments_json):
        if not self.function_call_client.wait_for_service(timeout_sec=2.0):
            return "Function call service is unavailable."

        req_payload = {
            "name": function_name,
            "arguments": arguments_json,
        }
        request = ChatGPT.Request()
        request.request_text = json.dumps(req_payload, ensure_ascii=False)

        future = self.function_call_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)

        if not future.done():
            return "Function call timeout."
        if future.result() is None:
            return f"Function call failed: {future.exception()}"
        return future.result().response_text

    def handle_tool_calls(self, tool_calls):
        for index, tool_call in enumerate(tool_calls):
            function_name = tool_call.function.name
            arguments_text = tool_call.function.arguments or "{}"
            try:
                arguments_obj = json.loads(arguments_text)
                arguments_text = json.dumps(arguments_obj, ensure_ascii=False)
            except json.JSONDecodeError:
                arguments_text = "{}"

            tool_result = self.call_robot_function_service(function_name, arguments_text)
            tool_call_id = tool_call.id or f"tool_call_{index}"
            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": str(tool_result),
            }
            self.add_message_to_history(tool_message)

    def run_dialog(self):
        enable_tools = True
        for _ in range(3):
            try:
                response = self.generate_chatgpt_response(enable_tools=enable_tools)
            except Exception as error:
                if enable_tools and self.robot_tools:
                    self.get_logger().warning(
                        f"Tool mode request failed, retrying without tools: {error}"
                    )
                    enable_tools = False
                    continue
                raise

            message = response.choices[0].message
            if message.tool_calls:
                self.publish_string("function_call", self.llm_response_type_publisher)
                self.add_message_to_history(self.tool_call_to_history_message(message))
                self.handle_tool_calls(message.tool_calls)
                continue

            reply_text = self.extract_text_content(message.content)
            if not reply_text:
                reply_text = "模型未返回文本内容。"
            self.add_message_to_history({"role": "assistant", "content": reply_text})
            return reply_text

        return "工具调用轮次超出上限，任务已中止。"

    def llm_callback(self, msg):
        self.get_logger().info("STATE: model_processing")
        user_prompt = msg.data
        self.get_logger().info(f"Input message received: {user_prompt}")

        self.add_message_to_history({"role": "user", "content": user_prompt})
        self.write_chat_history_to_json()

        try:
            reply_text = self.run_dialog()
        except Exception as error:
            self.get_logger().error(f"Model request failed: {error}")
            reply_text = f"模型调用失败: {error}"

        self.write_chat_history_to_json()
        self.publish_string("feedback_for_user", self.llm_response_type_publisher)
        self.publish_string(reply_text, self.llm_feedback_publisher)
        self.publish_string(reply_text, self.output_publisher)


def main(args=None):
    rclpy.init(args=args)
    chatgpt = ChatGPTNode()
    try:
        rclpy.spin(chatgpt)
    except KeyboardInterrupt:
        pass
    finally:
        chatgpt.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
