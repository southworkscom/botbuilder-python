# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import hashlib
import hmac
import json
import os
import uuid
import datetime
import time
import aiounittest
import requests


class SlackClient(aiounittest.AsyncTestCase):

    _slack_url_base: str = "https://slack.com/api"
    _slack_channel: str
    _slack_bot_token: str
    _slack_client_signing_secret: str
    _slack_verification_token: str
    _bot_name: str

    async def test_send_and_receive_slack_message(self):
        # Arrange
        self._get_environment_vars()
        echo_guid = str(uuid.uuid4())

        # Act
        await self._send_message_async(echo_guid)
        response = await self._receive_message_async()

        # Assert
        self.assertEqual(f"Echo: {echo_guid}", response)

    async def _receive_message_async(self):
        last_message = ""
        i = 0

        while "Echo" not in last_message and i < 60:
            url = (
                f"{self._slack_url_base}/conversations.history?token="
                f"{self._slack_bot_token}&channel={self._slack_channel}"
            )
            response = requests.get(url,)
            last_message = response.json()["messages"][0]["text"]

            time.sleep(1)
            i += 1

        return last_message

    async def _send_message_async(self, echo_guid: str):
        timestamp = str(int(datetime.datetime.utcnow().timestamp()))
        message = self._create_message(echo_guid)
        hub_signature = self._create_hub_signature(message, timestamp)
        headers = {
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": hub_signature,
            "Content-type": "application/json",
        }
        url = f"https://{self._bot_name}.azurewebsites.net/api/messages"

        requests.post(url, headers=headers, data=message)

    def _create_message(self, echo_guid: str):
        slack_event = {
            "client_msg_id": "client_msg_id",
            "type": "message",
            "text": echo_guid,
            "user": "userId",
            "channel": self._slack_channel,
            "channel_type": "im",
        }

        message = {
            "token": self._slack_verification_token,
            "team_id": "team_id",
            "api_app_id": "apiAppId",
            "event": slack_event,
            "type": "event_callback",
        }

        return json.dumps(message)

    def _create_hub_signature(self, message: str, timestamp: str):
        signature = ["v0", timestamp, message]
        base_string = ":".join(signature)

        computed_signature = "V0=" + hmac.new(
            bytes(self._slack_client_signing_secret, encoding="utf8"),
            msg=bytes(base_string, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest().upper().replace("-", "")

        return computed_signature

    def _get_environment_vars(self):
        self._slack_channel = os.getenv("SlackChannel")
        if not self._slack_channel:
            raise Exception('Environment variable "SlackChannel" not found.')

        self._slack_bot_token = os.getenv("SlackBotToken")
        if not self._slack_bot_token:
            raise Exception('Environment variable "SlackBotToken" not found.')

        self._slack_client_signing_secret = os.getenv("SlackClientSigningSecret")
        if not self._slack_client_signing_secret:
            raise Exception(
                'Environment variable "SlackClientSigningSecret" not found.'
            )

        self._slack_verification_token = os.getenv("SlackVerificationToken")
        if not self._slack_verification_token:
            raise Exception('Environment variable "SlackVerificationToken" not found.')

        self._bot_name = os.getenv("BotName")
        if not self._bot_name:
            raise Exception('Environment variable "BotName" not found.')
