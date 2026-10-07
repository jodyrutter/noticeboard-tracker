import { useEffect } from "react";
import { useResource } from "../hooks";
import { Icon } from "./UI";

export function NotificationBell({
  userId,
  open,
}: {
  userId: number;
  open: () => void;
}) {
  const resource = useResource<{ unread: number }>(
    `/notifications/${userId}/unread-count`,
  );
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible") resource.refresh();
    };
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener("noticeboard:notifications-changed", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("noticeboard:notifications-changed", refresh);
    };
  }, [resource.refresh]);
  return (
    <button
      className="icon-button notification-bell"
      aria-label="Open notifications"
      onClick={open}
    >
      <Icon name="notifications" />
      {!!resource.data?.unread && (
        <span
          className="badge"
          aria-label={`${resource.data.unread} unread notifications`}
        >
          {resource.data.unread}
        </span>
      )}
    </button>
  );
}
