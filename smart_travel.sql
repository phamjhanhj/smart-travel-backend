CREATE TABLE "users" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "email" varchar UNIQUE NOT NULL,
  "password_hash" text NOT NULL,
  "full_name" varchar NOT NULL,
  "avatar_url" varchar,
  "preferences_json" text,
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "trips" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "user_id" uuid NOT NULL,
  "title" varchar NOT NULL,
  "destination" varchar NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "budget" int,
  "num_travelers" int DEFAULT 1,
  "preferences" text,
  "status" varchar DEFAULT 'draft',
  "cover_image_url" varchar,
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "day_plans" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "trip_id" uuid NOT NULL,
  "day_number" int NOT NULL,
  "date" date NOT NULL
);

CREATE TABLE "activities" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "day_plan_id" uuid NOT NULL,
  "location_id" uuid,
  "title" varchar NOT NULL,
  "description" text,
  "type" varchar,
  "start_time" time,
  "end_time" time,
  "estimated_cost" int,
  "order_index" int DEFAULT 0,
  "booking_url" varchar,
  "notes" text
);

CREATE TABLE "locations" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "name" varchar NOT NULL,
  "address" text,
  "lat" float,
  "lng" float,
  "category" varchar,
  "google_place_id" varchar UNIQUE,
  "photo_url" varchar,
  "rating" float
);

CREATE TABLE "chat_history" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "trip_id" uuid NOT NULL,
  "role" varchar NOT NULL,
  "message" text NOT NULL,
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "ai_suggestions" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "trip_id" uuid NOT NULL,
  "type" varchar NOT NULL,
  "content_json" text NOT NULL,
  "status" varchar DEFAULT 'pending',
  "created_at" timestamp DEFAULT (now())
);

CREATE TABLE "budget_items" (
  "id" uuid PRIMARY KEY DEFAULT (gen_random_uuid()),
  "trip_id" uuid NOT NULL,
  "category" varchar NOT NULL,
  "label" varchar NOT NULL,
  "planned_amount" int DEFAULT 0,
  "actual_amount" int DEFAULT 0,
  "date" date,
  "created_at" timestamp DEFAULT (now())
);

CREATE UNIQUE INDEX ON "day_plans" ("trip_id", "day_number");

CREATE INDEX ON "activities" ("day_plan_id", "order_index");

CREATE INDEX ON "locations" ("google_place_id");

CREATE INDEX ON "locations" ("lat", "lng");

CREATE INDEX ON "chat_history" ("trip_id", "created_at");

CREATE INDEX ON "ai_suggestions" ("trip_id", "status");

CREATE INDEX ON "budget_items" ("trip_id");

COMMENT ON TABLE "users" IS 'Tài khoản người dùng';

COMMENT ON COLUMN "users"."preferences_json" IS 'JSON: { travel_style, budget_range, interests[] }';

COMMENT ON TABLE "trips" IS 'Mỗi chuyến đi của người dùng';

COMMENT ON COLUMN "trips"."budget" IS 'Tổng ngân sách dự kiến (VND)';

COMMENT ON COLUMN "trips"."preferences" IS 'Mô tả sở thích chuyến đi tự do';

COMMENT ON COLUMN "trips"."status" IS 'draft | active | completed';

COMMENT ON TABLE "day_plans" IS 'Kế hoạch theo từng ngày';

COMMENT ON COLUMN "day_plans"."day_number" IS 'Ngày thứ mấy trong chuyến đi (1, 2, 3...)';

COMMENT ON TABLE "activities" IS 'Hoạt động trong từng ngày';

COMMENT ON COLUMN "activities"."type" IS 'meal | attraction | hotel | transport | other';

COMMENT ON COLUMN "activities"."estimated_cost" IS 'Chi phí ước tính (VND)';

COMMENT ON COLUMN "activities"."order_index" IS 'Thứ tự hiển thị, dùng cho kéo thả';

COMMENT ON TABLE "locations" IS 'Địa điểm — có thể từ Google Places hoặc tự nhập';

COMMENT ON COLUMN "locations"."category" IS 'restaurant | attraction | hotel | cafe | other';

COMMENT ON COLUMN "locations"."google_place_id" IS 'ID từ Google Places API';

COMMENT ON COLUMN "locations"."rating" IS '1.0 - 5.0';

COMMENT ON TABLE "chat_history" IS 'Lịch sử hội thoại với AI theo từng chuyến đi';

COMMENT ON COLUMN "chat_history"."role" IS 'user | assistant';

COMMENT ON TABLE "ai_suggestions" IS 'Lưu gợi ý AI đã tạo — giúp tránh gợi ý lại nội dung bị từ chối';

COMMENT ON COLUMN "ai_suggestions"."type" IS 'itinerary | place | budget';

COMMENT ON COLUMN "ai_suggestions"."content_json" IS 'Nội dung gợi ý dạng JSON';

COMMENT ON COLUMN "ai_suggestions"."status" IS 'pending | accepted | rejected';

COMMENT ON TABLE "budget_items" IS 'Theo dõi ngân sách — planned vs actual';

COMMENT ON COLUMN "budget_items"."category" IS 'food | transport | hotel | activity | other';

COMMENT ON COLUMN "budget_items"."label" IS 'Tên khoản chi';

COMMENT ON COLUMN "budget_items"."planned_amount" IS 'Chi phí dự kiến (VND)';

COMMENT ON COLUMN "budget_items"."actual_amount" IS 'Chi phí thực tế (VND)';

ALTER TABLE "trips" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "day_plans" ADD FOREIGN KEY ("trip_id") REFERENCES "trips" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "activities" ADD FOREIGN KEY ("day_plan_id") REFERENCES "day_plans" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "activities" ADD FOREIGN KEY ("location_id") REFERENCES "locations" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "chat_history" ADD FOREIGN KEY ("trip_id") REFERENCES "trips" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ai_suggestions" ADD FOREIGN KEY ("trip_id") REFERENCES "trips" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "budget_items" ADD FOREIGN KEY ("trip_id") REFERENCES "trips" ("id") DEFERRABLE INITIALLY IMMEDIATE;
