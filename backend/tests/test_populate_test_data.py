"""Tests for backend/scripts/populate_test_data.py"""

import os
from unittest.mock import patch, MagicMock

import pytest


class TestGetCredentials:
    """Test OAuth credential building from env vars."""

    @patch.dict(os.environ, {
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
    })
    @patch("scripts.populate_test_data.InstalledAppFlow")
    @patch("scripts.populate_test_data.TOKEN_PATH")
    def test_builds_client_config_from_env_vars(self, mock_token_path, mock_flow_cls):
        mock_token_path.exists.return_value = False

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_config.return_value = mock_flow

        from scripts.populate_test_data import get_credentials

        creds = get_credentials()

        mock_flow_cls.from_client_config.assert_called_once()
        call_args = mock_flow_cls.from_client_config.call_args
        client_config = call_args[0][0]
        scopes = call_args[0][1]

        assert client_config["installed"]["client_id"] == "test-client-id.apps.googleusercontent.com"
        assert client_config["installed"]["client_secret"] == "test-client-secret"
        assert "https://www.googleapis.com/auth/calendar" in scopes
        assert "https://www.googleapis.com/auth/gmail.modify" in scopes
        assert creds is mock_creds

    @patch.dict(os.environ, {
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
    })
    @patch("scripts.populate_test_data.Credentials")
    @patch("scripts.populate_test_data.TOKEN_PATH")
    def test_loads_cached_token_when_valid(self, mock_token_path, mock_creds_cls):
        mock_token_path.exists.return_value = True
        mock_token_path.read_text.return_value = '{"token": "cached"}'

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_cls.from_authorized_user_info.return_value = mock_creds

        from scripts.populate_test_data import get_credentials

        creds = get_credentials()

        assert creds is mock_creds
        mock_creds_cls.from_authorized_user_info.assert_called_once()

    @patch.dict(os.environ, {
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
    })
    @patch("scripts.populate_test_data.InstalledAppFlow")
    @patch("scripts.populate_test_data.Request")
    @patch("scripts.populate_test_data.Credentials")
    @patch("scripts.populate_test_data.TOKEN_PATH")
    def test_refreshes_expired_token(self, mock_token_path, mock_creds_cls, mock_request_cls, mock_flow_cls):
        mock_token_path.exists.return_value = True
        mock_token_path.read_text.return_value = '{"token": "expired"}'

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds_cls.from_authorized_user_info.return_value = mock_creds

        from scripts.populate_test_data import get_credentials

        creds = get_credentials()

        mock_creds.refresh.assert_called_once()
        assert creds is mock_creds


class TestCalendarCleanup:
    """Test calendar cleanup deletes only title-matched events in Jun 1-5 range."""

    def _make_calendar_service(self, events_list):
        service = MagicMock()
        service.events.return_value.list.return_value.execute.return_value = {
            "items": events_list
        }
        return service

    def test_deletes_matching_events(self):
        from scripts.populate_test_data import cleanup_calendar_events

        events = [
            {"id": "evt1", "summary": "Team Standup"},
            {"id": "evt2", "summary": "Research Meeting"},
        ]
        service = self._make_calendar_service(events)

        cleanup_calendar_events(service)

        assert service.events.return_value.delete.return_value.execute.call_count == 2

    def test_skips_non_matching_events(self):
        from scripts.populate_test_data import cleanup_calendar_events

        events = [
            {"id": "evt1", "summary": "Team Standup"},
            {"id": "evt2", "summary": "Personal Dentist Appointment"},
        ]
        service = self._make_calendar_service(events)

        cleanup_calendar_events(service)

        delete_calls = service.events.return_value.delete.call_args_list
        assert len(delete_calls) == 1
        assert delete_calls[0][1]["eventId"] == "evt1"

    def test_uses_correct_time_range(self):
        from scripts.populate_test_data import cleanup_calendar_events

        service = self._make_calendar_service([])

        cleanup_calendar_events(service)

        list_call = service.events.return_value.list.call_args
        assert "2026-06-01" in list_call[1]["timeMin"]
        assert "2026-06-05" in list_call[1]["timeMax"]


class TestCalendarSeeding:
    """Test calendar seeding creates exactly 10 events with correct data."""

    def test_creates_exactly_10_events(self):
        from scripts.populate_test_data import seed_calendar_events

        service = MagicMock()

        seed_calendar_events(service)

        insert_calls = service.events.return_value.insert.call_args_list
        assert len(insert_calls) == 10

    def test_events_have_correct_timezone(self):
        from scripts.populate_test_data import seed_calendar_events

        service = MagicMock()

        seed_calendar_events(service)

        insert_calls = service.events.return_value.insert.call_args_list
        for call in insert_calls:
            body = call[1]["body"]
            assert body["start"]["timeZone"] == "Asia/Taipei"
            assert body["end"]["timeZone"] == "Asia/Taipei"

    def test_events_have_correct_summaries(self):
        from scripts.populate_test_data import seed_calendar_events, CALENDAR_EVENTS

        service = MagicMock()

        seed_calendar_events(service)

        insert_calls = service.events.return_value.insert.call_args_list
        summaries = [call[1]["body"]["summary"] for call in insert_calls]
        expected = [title for _, _, title in CALENDAR_EVENTS]
        assert summaries == expected

    def test_first_event_has_correct_time(self):
        from scripts.populate_test_data import seed_calendar_events

        service = MagicMock()

        seed_calendar_events(service)

        first_call = service.events.return_value.insert.call_args_list[0]
        body = first_call[1]["body"]
        assert body["start"]["dateTime"] == "2026-06-01T09:00:00"
        assert body["end"]["dateTime"] == "2026-06-01T10:00:00"


class TestGmailLabelManagement:
    """Test ensure_test_seed_label creates or finds the TEST_SEED label."""

    def test_creates_label_when_not_found(self):
        from scripts.populate_test_data import ensure_test_seed_label

        service = MagicMock()
        service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
            "labels": [{"name": "INBOX", "id": "INBOX"}]
        }
        service.users.return_value.labels.return_value.create.return_value.execute.return_value = {
            "id": "Label_new", "name": "TEST_SEED"
        }

        label_id = ensure_test_seed_label(service)

        assert label_id == "Label_new"
        service.users.return_value.labels.return_value.create.assert_called_once()

    def test_returns_existing_label_id(self):
        from scripts.populate_test_data import ensure_test_seed_label

        service = MagicMock()
        service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
            "labels": [
                {"name": "INBOX", "id": "INBOX"},
                {"name": "TEST_SEED", "id": "Label_existing"},
            ]
        }

        label_id = ensure_test_seed_label(service)

        assert label_id == "Label_existing"
        service.users.return_value.labels.return_value.create.assert_not_called()


class TestGmailCleanup:
    """Test email cleanup deletes only TEST_SEED-labeled messages."""

    def test_deletes_all_labeled_messages(self):
        from scripts.populate_test_data import cleanup_emails

        service = MagicMock()
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}, {"id": "msg3"}]
        }

        cleanup_emails(service, "Label_test")

        delete_calls = service.users.return_value.messages.return_value.delete.call_args_list
        assert len(delete_calls) == 3
        deleted_ids = [call[1]["id"] for call in delete_calls]
        assert deleted_ids == ["msg1", "msg2", "msg3"]

    def test_handles_no_messages(self):
        from scripts.populate_test_data import cleanup_emails

        service = MagicMock()
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

        cleanup_emails(service, "Label_test")

        service.users.return_value.messages.return_value.delete.assert_not_called()

    def test_queries_with_correct_label_id(self):
        from scripts.populate_test_data import cleanup_emails

        service = MagicMock()
        service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

        cleanup_emails(service, "Label_42")

        list_call = service.users.return_value.messages.return_value.list.call_args
        assert list_call[1]["labelIds"] == ["Label_42"]


class TestGmailSeeding:
    """Test email seeding inserts 8 emails with correct properties."""

    def test_inserts_exactly_8_emails(self):
        from scripts.populate_test_data import seed_emails

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        assert len(insert_calls) == 8

    def test_all_emails_are_unread(self):
        from scripts.populate_test_data import seed_emails

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        for call in insert_calls:
            body = call[1]["body"]
            assert "UNREAD" in body["labelIds"]

    def test_all_emails_tagged_with_label(self):
        from scripts.populate_test_data import seed_emails

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        for call in insert_calls:
            body = call[1]["body"]
            assert "Label_test" in body["labelIds"]

    def test_emails_have_correct_subjects(self):
        from scripts.populate_test_data import seed_emails, TEST_EMAILS
        import base64
        import email

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        subjects = []
        for call in insert_calls:
            raw = call[1]["body"]["raw"]
            msg_bytes = base64.urlsafe_b64decode(raw)
            msg = email.message_from_bytes(msg_bytes)
            subjects.append(msg["Subject"])

        expected_subjects = [e[1] for e in TEST_EMAILS]
        assert subjects == expected_subjects

    def test_emails_have_correct_from_addresses(self):
        from scripts.populate_test_data import seed_emails, TEST_EMAILS
        import base64
        import email

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        froms = []
        for call in insert_calls:
            raw = call[1]["body"]["raw"]
            msg_bytes = base64.urlsafe_b64decode(raw)
            msg = email.message_from_bytes(msg_bytes)
            froms.append(msg["From"])

        expected_froms = [e[0] for e in TEST_EMAILS]
        assert froms == expected_froms

    def test_emails_have_body_content(self):
        from scripts.populate_test_data import seed_emails
        import base64
        import email

        service = MagicMock()

        seed_emails(service, "Label_test")

        insert_calls = service.users.return_value.messages.return_value.insert.call_args_list
        for call in insert_calls:
            raw = call[1]["body"]["raw"]
            msg_bytes = base64.urlsafe_b64decode(raw)
            msg = email.message_from_bytes(msg_bytes)
            body = msg.get_payload(decode=True).decode()
            assert len(body) > 20


class TestMainOrchestration:
    """Test that main() calls cleanup then create in correct order."""

    @patch("scripts.populate_test_data.get_credentials")
    @patch("scripts.populate_test_data.build")
    def test_main_calls_in_correct_order(self, mock_build, mock_get_creds):
        from scripts.populate_test_data import main

        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_cal_service = MagicMock()
        mock_gmail_service = MagicMock()

        def build_side_effect(service_name, version, credentials):
            if service_name == "calendar":
                return mock_cal_service
            return mock_gmail_service

        mock_build.side_effect = build_side_effect

        mock_cal_service.events.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        mock_gmail_service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
            "labels": [{"name": "TEST_SEED", "id": "Label_1"}]
        }
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

        call_order = []
        original_events_list = mock_cal_service.events.return_value.list.return_value.execute
        original_events_list.side_effect = lambda: (
            call_order.append("cal_list"),
            {"items": []},
        )[-1]

        original_events_insert = mock_cal_service.events.return_value.insert.return_value.execute
        original_events_insert.side_effect = lambda: call_order.append("cal_insert")

        original_msg_list = mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute
        original_msg_list.side_effect = lambda: (
            call_order.append("gmail_list"),
            {},
        )[-1]

        original_msg_insert = mock_gmail_service.users.return_value.messages.return_value.insert.return_value.execute
        original_msg_insert.side_effect = lambda: call_order.append("gmail_insert")

        main()

        assert call_order[0] == "cal_list"
        cal_insert_idx = call_order.index("cal_insert")
        gmail_list_idx = call_order.index("gmail_list")
        gmail_insert_idx = call_order.index("gmail_insert")

        assert cal_insert_idx > 0
        assert gmail_list_idx > 0
        assert gmail_insert_idx > gmail_list_idx

    @patch("scripts.populate_test_data.get_credentials")
    @patch("scripts.populate_test_data.build")
    def test_main_builds_both_services(self, mock_build, mock_get_creds):
        from scripts.populate_test_data import main

        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = {
            "labels": [{"name": "TEST_SEED", "id": "Label_1"}]
        }
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {}

        main()

        build_calls = mock_build.call_args_list
        service_names = [call[0][0] for call in build_calls]
        assert "calendar" in service_names
        assert "gmail" in service_names
