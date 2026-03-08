import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import Navigation from "./components/shared/Navigation";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ConsumerDashboard from "./pages/consumer/ConsumerDashboard";
import ProductDetailPage from "./pages/consumer/ProductDetailPage";
import FarmerDashboard from "./pages/farmer/FarmerDashboard";
import NotFoundPage from "./pages/NotFoundPage";
import "./App.css";

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Consumer Routes */}
            <Route path="/consumer/dashboard" element={<ConsumerDashboard />} />
            <Route
              path="/consumer/products/:productId"
              element={
                <ProtectedRoute requiredRole="consumer">
                  <ProductDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/consumer/orders"
              element={
                <ProtectedRoute requiredRole="consumer">
                  <div className="container mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold">My Orders</h1>
                    <p className="text-gray-600 mt-2">Coming soon...</p>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* Farmer Routes */}
            <Route
              path="/farmer/dashboard"
              element={
                <ProtectedRoute requiredRole="farmer">
                  <FarmerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/products/new"
              element={
                <ProtectedRoute requiredRole="farmer">
                  <div className="container mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold">Add New Product</h1>
                    <p className="text-gray-600 mt-2">Coming soon...</p>
                  </div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/products/:productId"
              element={
                <ProtectedRoute requiredRole="farmer">
                  <div className="container mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold">Product Details</h1>
                    <p className="text-gray-600 mt-2">Coming soon...</p>
                  </div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/products/:productId/edit"
              element={
                <ProtectedRoute requiredRole="farmer">
                  <div className="container mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold">Edit Product</h1>
                    <p className="text-gray-600 mt-2">Coming soon...</p>
                  </div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/farmer/analytics"
              element={
                <ProtectedRoute requiredRole="farmer">
                  <div className="container mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold">Analytics</h1>
                    <p className="text-gray-600 mt-2">Coming soon...</p>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 404 Route */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
