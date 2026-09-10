/** Mirrors the Pydantic models in backend/app/models/schemas.py. */

export type AffiliateLink = {
  id: string;
  hotel_name: string;
  location: string;
  booking_url: string;
  created_at: string | null;
};

export type FlightLink = {
  id: string;
  destination_city: string;
  destination_country: string | null;
  origin_city: string | null;
  airline: string | null;
  booking_url: string;
  created_at: string | null;
};

export type Storefront = {
  id: string;
  creator_id: string;
  video_url: string;
  video_title: string;
  created_at: string | null;
  affiliate_links: AffiliateLink[];
  flight_links: FlightLink[];
};

export type GenerateStorefrontResponse = {
  storefront_id: string;
  video_title: string;
  hotels_found: number;
  flights_found: number;
  marker_used: string;
  marker_is_creators: boolean;
};

/** Shape of every non-2xx body from the FastAPI backend. */
export type ApiError = {
  code: string;
  message: string;
};
