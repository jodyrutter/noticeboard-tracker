from datetime import date
from services.trainee_service import get_all_trainees, create_trainee

trainee_id = create_trainee(
    2,                 # existing user_id
    1,                 # existing cohort_id
    "ACTIVE",
    date.today()
)

print("Created trainee:", trainee_id)
print(get_all_trainees())