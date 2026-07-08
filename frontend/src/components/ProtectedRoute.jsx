import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { canAccessRoute } from "../utils/permissions.js";

export default function ProtectedRoute({ children, roles = [], moduleName = null }) {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!canAccessRoute(user, roles, moduleName)) {
    return <Navigate to="/" replace />;
  }
  return children;
}
