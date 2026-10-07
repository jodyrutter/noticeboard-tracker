from unittest.mock import MagicMock
import pytest
from services import assignment_service, plan_service, progress_service, tracking_service, workflow_notifications


@pytest.fixture
def db(monkeypatch):
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    for module in (assignment_service, plan_service, progress_service, tracking_service):
        monkeypatch.setattr(module, "get_connection", lambda: connection)
    return connection, cursor


def notification_calls(cursor):
    return [c for c in cursor.execute.call_args_list if "INSERT INTO notifications" in c.args[0]]


def test_assignment_notifies_once_and_failure_rolls_back(db):
    connection, cursor = db
    cursor.fetchone.return_value = (12,)
    assert assignment_service.assign_plan_to_trainee(3,7) == 12
    assert len(notification_calls(cursor)) == 1
    assert notification_calls(cursor)[0].args[1] == ("Training plan assigned: ",3,[7])
    cursor.execute.side_effect = lambda query, *args: (_ for _ in ()).throw(RuntimeError("notification failed")) if "INSERT INTO notifications" in query else None
    with pytest.raises(RuntimeError):
        assignment_service.assign_plan_to_trainee(3,7)
    assert connection.__exit__.call_args.args[0] is RuntimeError


def test_duplicate_assignment_does_not_notify(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    with pytest.raises(assignment_service.AlreadyAssignedError):
        assignment_service.assign_plan_to_trainee(3,7)
    assert not notification_calls(cursor)


def test_bulk_noop_does_not_notify(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(3,),None]
    cursor.fetchall.side_effect = [[(7,)],[],[(7,)]]
    assert assignment_service.update_plan_assignments(3,[7],[9]) == [7]
    assert not notification_calls(cursor)


def test_plan_edit_notifies_only_when_changed(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(3,),None]
    assert plan_service.update_plan(3,"Title",None,None) == 3
    assert not notification_calls(cursor)
    cursor.fetchone.side_effect = [(3,),(3,)]
    assert plan_service.update_plan(3,"New title",None,None) == 3
    assert len(notification_calls(cursor)) == 1
    assert "DISTINCT t.user_id" in notification_calls(cursor)[0].args[0]


def test_progress_notifies_current_manager_owner_only(db):
    connection, cursor = db
    cursor.fetchone.return_value = (5,)
    assert progress_service.create_progress_report(7,3,"BLOCKED","Help",8) == 5
    call = notification_calls(cursor)[0]
    assert call.args[1] == ("BLOCKED",8,3)
    assert "manager.id = p.created_by" in call.args[0]
    assert "manager.role = 'MANAGER'" in call.args[0]


def test_tracking_summarizes_current_assignments(db):
    connection, cursor = db
    rows = [{"status":"COMPLETED","overdue":False,"missing_report":False},
            {"status":"BLOCKED","overdue":True,"missing_report":False},
            {"status":"NOT_STARTED","overdue":True,"missing_report":True}]
    cursor.fetchall.side_effect = [rows,[{"trainee_id":5,"name":"Unassigned"}]]
    result = tracking_service.get_tracking()
    assert result["summary"] == {"NOT_STARTED":1,"IN_PROGRESS":0,"COMPLETED":1,"BLOCKED":1,"total_assignments":3,"overdue":2,"missing_reports":1,"unassigned_trainees":1}
    query = cursor.execute.call_args_list[0].args[0]
    assert "ORDER BY pr.submitted_at DESC, pr.id DESC LIMIT 1" in query
    assert "LEFT JOIN LATERAL" in query
    assert "<> 'COMPLETED'" in query


def test_empty_tracking(db):
    connection, cursor = db
    cursor.fetchall.side_effect = [[],[]]
    assert all(n == 0 for n in tracking_service.get_tracking()["summary"].values())
