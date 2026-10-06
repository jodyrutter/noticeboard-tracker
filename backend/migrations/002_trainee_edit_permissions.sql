BEGIN;

GRANT UPDATE (cohort_id, status, onboarding_date)
    ON TABLE public.trainees TO noticeboard_app;

COMMIT;
