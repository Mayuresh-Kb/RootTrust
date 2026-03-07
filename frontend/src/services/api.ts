import axios, { type AxiosInstance, type AxiosError } from "axios";
import type {
  AuthResponse,
  User,
  Product,
  Order,
  Review,
  Referral,
  Promotion,
  LimitedRelease,
  FarmerAnalytics,
  NotificationPreferences,
  PaginatedResponse,
} from "../types";

// Create axios instance with base configuration
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:3000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("authToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem("authToken");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

// Authentication API
export const authApi = {
  register: async (data: {
    email: string;
    password: string;
    role: "farmer" | "consumer";
    firstName: string;
    lastName: string;
    phone: string;
  }) => {
    const response = await api.post<AuthResponse>("/auth/register", data);
    return response.data;
  },

  login: async (email: string, password: string) => {
    const response = await api.post<AuthResponse>("/auth/login", {
      email,
      password,
    });
    return response.data;
  },

  verify: async () => {
    const response = await api.get<{ valid: boolean; user: User }>(
      "/auth/verify",
    );
    return response.data;
  },
};

// Product API
export const productApi = {
  create: async (productData: Partial<Product>) => {
    const response = await api.post<{
      productId: string;
      uploadUrls: string[];
    }>("/products", productData);
    return response.data;
  },

  list: async (params?: {
    category?: string;
    seasonal?: boolean;
    giTag?: boolean;
    search?: string;
    limit?: number;
    cursor?: string;
  }) => {
    const response = await api.get<PaginatedResponse<Product>>("/products", {
      params,
    });
    return response.data;
  },

  getById: async (productId: string) => {
    const response = await api.get<Product>(`/products/${productId}`);
    return response.data;
  },

  update: async (productId: string, updates: Partial<Product>) => {
    const response = await api.put<Product>(`/products/${productId}`, updates);
    return response.data;
  },

  delete: async (productId: string) => {
    await api.delete(`/products/${productId}`);
  },

  uploadImages: async (productId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("images", file));
    const response = await api.post(`/products/${productId}/images`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },
};

// AI API
export const aiApi = {
  verifyProduct: async (productId: string) => {
    const response = await api.post(`/ai/verify-product`, { productId });
    return response.data;
  },

  generateDescription: async (productId: string) => {
    const response = await api.post<{ description: string }>(
      `/ai/generate-description`,
      { productId },
    );
    return response.data;
  },

  generateNames: async (productData: Partial<Product>) => {
    const response = await api.post<{ names: string[] }>(
      `/ai/generate-names`,
      productData,
    );
    return response.data;
  },

  enhanceDescription: async (description: string) => {
    const response = await api.post<{ enhancedDescription: string }>(
      `/ai/enhance-description`,
      { description },
    );
    return response.data;
  },

  generateSocial: async (productId: string) => {
    const response = await api.post<{ socialText: string }>(
      `/ai/generate-social`,
      { productId },
    );
    return response.data;
  },

  generateLaunch: async (productId: string) => {
    const response = await api.post<{ launchText: string }>(
      `/ai/generate-launch`,
      { productId },
    );
    return response.data;
  },
};

// Order API
export const orderApi = {
  create: async (orderData: {
    productId: string;
    quantity: number;
    deliveryAddress: any;
    referralCode?: string;
  }) => {
    const response = await api.post<{
      orderId: string;
      totalAmount: number;
      estimatedDeliveryDate: string;
    }>("/orders", orderData);
    return response.data;
  },

  list: async () => {
    const response = await api.get<Order[]>("/orders");
    return response.data;
  },

  getById: async (orderId: string) => {
    const response = await api.get<Order>(`/orders/${orderId}`);
    return response.data;
  },

  updateStatus: async (orderId: string, status: string) => {
    const response = await api.put<Order>(`/orders/${orderId}/status`, {
      status,
    });
    return response.data;
  },
};

// Payment API
export const paymentApi = {
  initiate: async (orderId: string) => {
    const response = await api.post<{ paymentUrl: string; sessionId: string }>(
      "/payments/initiate",
      { orderId },
    );
    return response.data;
  },

  getStatus: async (transactionId: string) => {
    const response = await api.get(`/payments/${transactionId}`);
    return response.data;
  },
};

// Review API
export const reviewApi = {
  create: async (reviewData: {
    productId: string;
    orderId: string;
    rating: number;
    reviewText: string;
    photoUploadCount?: number;
  }) => {
    const response = await api.post<{
      reviewId: string;
      photoUploadUrls?: string[];
    }>("/reviews", reviewData);
    return response.data;
  },

  getByProduct: async (productId: string) => {
    const response = await api.get<Review[]>(`/reviews/product/${productId}`);
    return response.data;
  },

  getByFarmer: async (farmerId: string) => {
    const response = await api.get<Review[]>(`/reviews/farmer/${farmerId}`);
    return response.data;
  },
};

// Referral API
export const referralApi = {
  generate: async (productId: string) => {
    const response = await api.post<{
      referralCode: string;
      referralUrl: string;
    }>("/referrals/generate", {
      productId,
    });
    return response.data;
  },

  validate: async (code: string) => {
    const response = await api.get<Referral>(`/referrals/${code}`);
    return response.data;
  },

  track: async (referralCode: string, orderId: string) => {
    await api.post("/referrals/track", { referralCode, orderId });
  },

  getRewards: async () => {
    const response = await api.get<{
      rewardBalance: number;
      totalConversions: number;
      redemptionOptions: any[];
    }>("/referrals/rewards");
    return response.data;
  },
};

// Promotion API
export const promotionApi = {
  create: async (promotionData: {
    productId: string;
    budget: number;
    duration: number;
  }) => {
    const response = await api.post<Promotion>("/promotions", promotionData);
    return response.data;
  },

  list: async () => {
    const response = await api.get<Promotion[]>("/promotions");
    return response.data;
  },

  getMetrics: async (promotionId: string) => {
    const response = await api.get(`/promotions/${promotionId}/metrics`);
    return response.data;
  },

  update: async (promotionId: string, updates: Partial<Promotion>) => {
    const response = await api.put<Promotion>(
      `/promotions/${promotionId}`,
      updates,
    );
    return response.data;
  },
};

// Limited Release API
export const limitedReleaseApi = {
  create: async (releaseData: {
    productId: string;
    releaseName: string;
    quantityLimit: number;
    duration: number;
  }) => {
    const response = await api.post<LimitedRelease>(
      "/limited-releases",
      releaseData,
    );
    return response.data;
  },

  list: async () => {
    const response = await api.get<LimitedRelease[]>("/limited-releases");
    return response.data;
  },

  getById: async (releaseId: string) => {
    const response = await api.get<LimitedRelease>(
      `/limited-releases/${releaseId}`,
    );
    return response.data;
  },

  purchase: async (releaseId: string) => {
    const response = await api.post<{ orderId: string }>(
      `/limited-releases/${releaseId}/purchase`,
    );
    return response.data;
  },
};

// Analytics API
export const analyticsApi = {
  getFarmerAnalytics: async (farmerId: string) => {
    const response = await api.get<FarmerAnalytics>(
      `/analytics/farmer/${farmerId}`,
    );
    return response.data;
  },

  getProductAnalytics: async (productId: string) => {
    const response = await api.get(`/analytics/product/${productId}`);
    return response.data;
  },

  getTrends: async () => {
    const response = await api.get("/analytics/trends");
    return response.data;
  },

  getFarmerBonuses: async (farmerId: string) => {
    const response = await api.get(`/analytics/farmer/${farmerId}/bonuses`);
    return response.data;
  },
};

// Notification API
export const notificationApi = {
  updatePreferences: async (preferences: NotificationPreferences) => {
    const response = await api.put<NotificationPreferences>(
      "/notifications/preferences",
      preferences,
    );
    return response.data;
  },

  unsubscribe: async (email: string) => {
    await api.post("/notifications/unsubscribe", { email });
  },
};

export default api;
