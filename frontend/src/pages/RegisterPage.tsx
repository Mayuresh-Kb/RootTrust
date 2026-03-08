import { Link } from "react-router-dom";
import RegistrationForm from "../components/auth/RegistrationForm";

export default function RegisterPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-gray-600">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-primary hover:text-primary-700 font-semibold"
            >
              Sign in
            </Link>
          </p>
        </div>
        <RegistrationForm />
      </div>
    </div>
  );
}
