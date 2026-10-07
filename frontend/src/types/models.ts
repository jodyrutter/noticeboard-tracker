export type Role = "HR" | "MANAGER" | "TRAINEE";
export interface User {
  user_id: number;
  name: string;
  email: string;
  role: Role;
}
export type TraineeStatus = "ACTIVE" | "INACTIVE" | "COMPLETED" | "WITHDRAWN";
export type ProgressStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "BLOCKED";
export interface Trainee {
  id: number;
  user_id: number;
  name: string;
  email: string;
  cohort_id: number | null;
  cohort_name: string | null;
  status: TraineeStatus;
  onboarding_date: string;
}
export interface Cohort {
  id: number;
  name: string;
  start_date: string;
  end_date: string | null;
}
export interface Plan {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  created_by: number;
}
export interface Progress {
  id: number;
  trainee_id: number;
  plan_id: number;
  status: ProgressStatus;
  comments: string | null;
  submitted_at: string;
}
export interface Notice {
  id: number;
  user_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}
export interface Summary {
  total_trainees: number;
  active_trainees: number;
  total_cohorts: number;
  completed_reports: number;
  in_progress_reports: number;
  blocked_reports: number;
  not_started_reports?: number;
  missing_reports: number;
}
