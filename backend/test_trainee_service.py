from datetime import date
from services.trainee_service import get_all_trainees, create_trainee


if __name__ == "__main__":
    trainee_id = create_trainee(
        2,                 # existing user_id
        1,                 # existing cohort_id
        "ACTIVE",
        date.today()
    )

    print("Created trainee:", trainee_id)

    print(get_all_trainees())
