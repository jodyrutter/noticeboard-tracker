BEGIN;

ALTER TABLE public.trainees
    ADD CONSTRAINT trainees_status_allowed
    CHECK (status IS NOT NULL AND status IN ('ACTIVE', 'INACTIVE', 'COMPLETED', 'WITHDRAWN')) NOT VALID;

ALTER TABLE public.progress_reports
    ADD CONSTRAINT progress_reports_status_allowed
    CHECK (status IS NOT NULL AND status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')) NOT VALID;

ALTER TABLE public.trainees VALIDATE CONSTRAINT trainees_status_allowed;
ALTER TABLE public.progress_reports VALIDATE CONSTRAINT progress_reports_status_allowed;

GRANT UPDATE (role) ON public.users TO noticeboard_app;

COMMIT;
