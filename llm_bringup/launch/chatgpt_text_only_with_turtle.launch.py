#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="turtlesim",
                executable="turtlesim_node",
                name="turtlesim_node",
                output="screen",
            ),
            Node(
                package="llm_robot",
                executable="turtle_robot",
                name="turtle_robot",
                output="screen",
            ),
            Node(
                package="llm_model",
                executable="chatgpt",
                name="chatgpt",
                output="screen",
            ),
        ]
    )
