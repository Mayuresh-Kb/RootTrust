import { Link } from "react-router-dom";
import LoginForm from "../components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Sign in to RootTrust
          </h2>
          <p className="mt-2 text-gray-600">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-primary hover:text-primary-700 font-semibold"
            >
              Register here
            </Link>
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
