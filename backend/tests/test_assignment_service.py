from unittest.mock import MagicMock
import pytest
from psycopg2.errors import ForeignKeyViolation
from services import assignment_service as service, cohort_service


@pytest.fixture
def db(monkeypatch):
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    for module in (service, cohort_service):
        monkeypatch.setattr(module, "get_connection", lambda: connection)
    return connection, cursor


def test_duplicate_assignment_conflict_and_cleanup(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    with pytest.raises(service.AlreadyAssignedError):
        service.assign_plan_to_trainee(1,6)
    assert "ON CONFLICT (plan_id, trainee_id) DO NOTHING" in cursor.execute.call_args.args[0]
    assert connection.__exit__.call_args.args[0] is service.AlreadyAssignedError
    connection.close.assert_called_once()


def test_new_assignment(db):
    connection, cursor = db
    cursor.fetchone.return_value = (12,)
    assert service.assign_plan_to_trainee(1,6) == 12
    assert cursor.execute.call_args.args[1] == (1,6)
    connection.close.assert_called_once()


def test_missing_assignment_target_cleanup(db):
    connection, cursor = db
    cursor.execute.side_effect = ForeignKeyViolation()
    with pytest.raises(service.AssignmentReferenceError):
        service.assign_plan_to_trainee(1,6)
    connection.close.assert_called_once()


def test_cohort_assignments_skip_duplicates(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(1,),(2,),None,(12,)]
    cursor.fetchall.return_value = [(6,),(7,)]
    assert service.assign_plan_to_cohort(1,2) == [12]
    connection.close.assert_called_once()


def test_bulk_cohort_changes_only_apply_deltas(db):
    connection, cursor = db
    cursor.fetchone.return_value = (1,)
    cursor.fetchall.side_effect = [[(7,),(9,)],[(7,),(9,)]]
    assert cohort_service.update_cohort_members(1,[7],[9]) == [7,9]
    query, params = cursor.execute.call_args.args
    assert params == ([7],1,[7],1,[9])
    assert "cohort_id = %s AND id = ANY(%s)" in query
    connection.close.assert_called_once()


def test_missing_member_rolls_back_before_updates(db):
    connection, cursor = db
    cursor.fetchone.return_value = (1,)
    cursor.fetchall.return_value = [(7,)]
    with pytest.raises(cohort_service.MissingCohortMemberError):
        cohort_service.update_cohort_members(1,[7,9],[])
    assert not any("UPDATE trainees" in c.args[0] for c in cursor.execute.call_args_list)
    connection.close.assert_called_once()
