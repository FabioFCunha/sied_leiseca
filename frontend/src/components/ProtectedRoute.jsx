import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { canAccessRoute } from "../utils/permissions.js";
import { useState, useEffect } from "react";
import LGPDModal from "./LGPDModal.jsx";

export default function ProtectedRoute({ children, roles = [], moduleName = null }) {
  const { isAuthenticated, user } = useAuth();
  const [lgpdAccepted, setLgpdAccepted] = useState(Boolean(user?.lgpd_consent_at));

  // If user object updates from context or props, update state
  useEffect(() => {
    if (user) {
      setLgpdAccepted(Boolean(user.lgpd_consent_at));
    }
  }, [user]);

  if (!isAuthenticated) {
    const loginPath = window.location.pathname.startsWith("/app")
      ? "/app/login"
      : "/login";

    return <Navigate to={loginPath} replace />;
  }

  if (!canAccessRoute(user, roles, moduleName)) {
    return <Navigate to="/" replace />;
  }

  return (
    <>
      {!lgpdAccepted && (
        <LGPDModal onConsent={(updatedUser) => setLgpdAccepted(true)} />
      )}
      {children}
    </>
  );
}