from flask import flash, session

from src import _page_flashes


def test_string_payload_is_a_notice_keyed_by_its_category(app):
    with app.test_request_context('/'):
        flash('已更新設定', 'success')
        # any category is a toast level: no carve-out, it still surfaces as a notice
        flash('unexpected level still shows', 'legacy')

        split = _page_flashes()

        assert split == {
            'flash': {'success': '已更新設定', 'legacy': 'unexpected level still shows'},
            'errors': {},
        }


def test_structured_payload_is_a_field_error(app):
    with app.test_request_context('/'):
        flash({'field': 'deadline', 'message': 'Deadline must be a valid date'}, 'error')

        split = _page_flashes()

        # fields stay snake_case here; the JSON provider camelizes them on the way out
        assert split == {
            'flash': {},
            'errors': {'deadline': 'Deadline must be a valid date'},
        }


def test_mixed_flashes_fill_both_props_and_are_read_once(app):
    with app.test_request_context('/'):
        flash('已成功建立票價追蹤', 'success')
        flash({'field': 'deadline', 'message': 'Deadline must be a valid date'}, 'error')
        flash({'field': 'notify_per_leg', 'message': 'Invalid notify_per_leg'}, 'error')

        split = _page_flashes()

        assert split == {
            'flash': {'success': '已成功建立票價追蹤'},
            'errors': {
                'deadline': 'Deadline must be a valid date',
                'notify_per_leg': 'Invalid notify_per_leg',
            },
        }
        # one read pops the queue, so both shares see the same split
        assert _page_flashes() is split
        assert '_flashes' not in session
