// User Types
export type UserRole = "farmer" | "consumer";

export interface User {
  userId: string;
  email: string;
  role: UserRole;
  firstName: string;
  lastName: string;
  phone: string;
  createdAt: string;
}

export interface AuthResponse {
  token: string;
  userId: string;
  role: UserRole;
  expiresIn: number;
}

// Product Types
export type ProductCategory =
  | "vegetables"
  | "fruits"
  | "grains"
  | "spices"
  | "dairy";
export type VerificationStatus =
  | "pending"
  | "approved"
  | "flagged"
  | "rejected";

export interface GITag {
  hasTag: boolean;
  tagName?: string;
  region?: string;
}

export interface SeasonalInfo {
  isSeasonal: boolean;
  seasonStart?: string;
  seasonEnd?: string;
}

export interface ProductImage {
  url: string;
  isPrimary: boolean;
}

export interface Product {
  productId: string;
  farmerId: string;
  farmerName?: string;
  name: string;
  category: ProductCategory;
  description: string;
  price: number;
  unit: string;
  giTag: GITag;
  seasonal: SeasonalInfo;
  images: ProductImage[];
  verificationStatus: VerificationStatus;
  fraudRiskScore?: number;
  authenticityConfidence?: number;
  aiExplanation?: string;
  predictedMarketPrice?: number;
  quantity: number;
  averageRating: number;
  totalReviews: number;
  totalSales: number;
  viewCount: number;
  currentViewers: number;
  recentPurchaseCount: number;
  createdAt: string;
  updatedAt: string;
}

// Order Types
export type OrderStatus =
  | "pending"
  | "confirmed"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "failed";
export type PaymentStatus = "pending" | "completed" | "failed" | "refunded";

export interface DeliveryAddress {
  street: string;
  city: string;
  state: string;
  pincode: string;
}

export interface Order {
  orderId: string;
  consumerId: string;
  farmerId: string;
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalAmount: number;
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  transactionId?: string;
  deliveryAddress: DeliveryAddress;
  estimatedDeliveryDate: string;
  actualDeliveryDate?: string;
  referralCode?: string;
  createdAt: string;
  updatedAt: string;
}

// Review Types
export interface ReviewPhoto {
  url: string;
  caption?: string;
}

export interface Review {
  reviewId: string;
  productId: string;
  farmerId: string;
  consumerId: string;
  orderId: string;
  rating: number;
  reviewText: string;
  photos: ReviewPhoto[];
  helpful: number;
  createdAt: string;
}

// Referral Types
export interface ReferralConversion {
  referredUserId: string;
  orderId: string;
  rewardAmount: number;
  convertedAt: string;
}

export interface Referral {
  referralCode: string;
  referrerId: string;
  productId: string;
  conversions: ReferralConversion[];
  totalConversions: number;
  totalRewards: number;
  createdAt: string;
}

// Promotion Types
export type PromotionStatus = "active" | "paused" | "completed" | "cancelled";

export interface PromotionMetrics {
  views: number;
  clicks: number;
  conversions: number;
  spent: number;
}

export interface Promotion {
  promotionId: string;
  farmerId: string;
  productId: string;
  budget: number;
  duration: number;
  status: PromotionStatus;
  startDate: string;
  endDate: string;
  metrics: PromotionMetrics;
  aiGeneratedAdCopy: string;
  createdAt: string;
}

// Limited Release Types
export type LimitedReleaseStatus =
  | "scheduled"
  | "active"
  | "sold_out"
  | "expired";

export interface LimitedRelease {
  releaseId: string;
  farmerId: string;
  productId: string;
  releaseName: string;
  quantityLimit: number;
  quantityRemaining: number;
  duration: number;
  startDate: string;
  endDate: string;
  status: LimitedReleaseStatus;
  createdAt: string;
}

// Analytics Types
export interface FarmerAnalytics {
  monthlyRevenue: number;
  totalSales: number;
  averageRating: number;
  totalReviews: number;
  viewCounts: Record<string, number>;
  conversionRates: Record<string, number>;
  topProducts: Array<{
    productId: string;
    productName: string;
    revenue: number;
  }>;
}

// Notification Types
export interface NotificationPreferences {
  newProducts: boolean;
  promotions: boolean;
  orderUpdates: boolean;
  reviewRequests: boolean;
  limitedReleases: boolean;
  farmerBonuses: boolean;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  nextCursor?: string;
  hasMore: boolean;
}
