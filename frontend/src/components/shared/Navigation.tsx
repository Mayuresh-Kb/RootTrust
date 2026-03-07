import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

export default function Navigation() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  if (!user) {
    return (
      <nav className="bg-primary text-white shadow-lg border-b border-primary/20">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <Link
              to="/"
              className="text-2xl font-bold hover:opacity-90 transition flex items-center"
            >
              <svg
                className="w-8 h-8 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"
                  clipRule="evenodd"
                />
              </svg>
              RootTrust
            </Link>
            <div className="flex gap-3">
              <Link
                to="/login"
                className="px-5 py-2 rounded-lg hover:bg-white/10 transition font-medium"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="px-5 py-2 bg-white text-primary rounded-lg hover:bg-gray-50 transition font-semibold shadow-md"
              >
                Register
              </Link>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  const isConsumer = user.role === "consumer";
  const isFarmer = user.role === "farmer";

  return (
    <nav className="bg-primary text-white shadow-lg border-b border-primary/20">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link
            to="/"
            className="text-2xl font-bold hover:opacity-90 transition flex items-center"
          >
            <svg
              className="w-8 h-8 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"
                clipRule="evenodd"
              />
            </svg>
            RootTrust
          </Link>

          <div className="flex items-center gap-8">
            {isConsumer && (
              <>
                <Link
                  to="/consumer/dashboard"
                  className="hover:text-secondary transition font-medium"
                >
                  Marketplace
                </Link>
                <Link
                  to="/consumer/orders"
                  className="hover:text-secondary transition font-medium"
                >
                  My Orders
                </Link>
              </>
            )}

            {isFarmer && (
              <>
                <Link
                  to="/farmer/dashboard"
                  className="hover:text-secondary transition font-medium"
                >
                  My Products
                </Link>
                <Link
                  to="/farmer/products/new"
                  className="hover:text-secondary transition font-medium"
                >
                  Add Product
                </Link>
                <Link
                  to="/farmer/analytics"
                  className="hover:text-secondary transition font-medium"
                >
                  Analytics
                </Link>
              </>
            )}

            <div className="flex items-center gap-4 ml-4 pl-4 border-l border-white/20">
              <span className="text-sm font-medium">
                {user.email}{" "}
                <span className="text-secondary">({user.role})</span>
              </span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
