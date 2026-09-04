--
-- PostgreSQL database dump
--

\restrict TYBGK8GkvQX2MnLn8eKO0zhfkGoyxJWun4RofarQNMICZcj7rebfCGZDPjta03O

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: customerstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.customerstatus AS ENUM (
    'PENDING',
    'ACTIVE',
    'SUSPENDED',
    'REJECTED'
);


ALTER TYPE public.customerstatus OWNER TO postgres;

--
-- Name: platform; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.platform AS ENUM (
    'TELEGRAM',
    'EITAA',
    'BALE'
);


ALTER TYPE public.platform OWNER TO postgres;

--
-- Name: productpublishstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.productpublishstatus AS ENUM (
    'PENDING',
    'SCHEDULED',
    'PUBLISHED',
    'FAILED',
    'SKIPPED'
);


ALTER TYPE public.productpublishstatus OWNER TO postgres;

--
-- Name: subscriptionstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.subscriptionstatus AS ENUM (
    'PENDING',
    'ACTIVE',
    'EXPIRED',
    'GRACE',
    'SUSPENDED'
);


ALTER TYPE public.subscriptionstatus OWNER TO postgres;

--
-- Name: tokensource; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tokensource AS ENUM (
    'MONTHLY',
    'PURCHASED'
);


ALTER TYPE public.tokensource OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_link_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account_link_codes (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    link_code character varying(10) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    is_used boolean NOT NULL,
    failed_attempts integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.account_link_codes OWNER TO postgres;

--
-- Name: account_link_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.account_link_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_link_codes_id_seq OWNER TO postgres;

--
-- Name: account_link_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.account_link_codes_id_seq OWNED BY public.account_link_codes.id;


--
-- Name: ai_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ai_tokens (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    source public.tokensource NOT NULL,
    total_amount integer NOT NULL,
    used_amount integer NOT NULL,
    remaining_amount integer NOT NULL,
    expires_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_tokens OWNER TO postgres;

--
-- Name: ai_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ai_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ai_tokens_id_seq OWNER TO postgres;

--
-- Name: ai_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ai_tokens_id_seq OWNED BY public.ai_tokens.id;


--
-- Name: ai_usage_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ai_usage_logs (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    product_id integer,
    usage_type character varying(30) NOT NULL,
    tokens_used integer NOT NULL,
    model_used character varying(100) NOT NULL,
    accepted boolean NOT NULL,
    raw_response text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_usage_logs OWNER TO postgres;

--
-- Name: ai_usage_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ai_usage_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ai_usage_logs_id_seq OWNER TO postgres;

--
-- Name: ai_usage_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ai_usage_logs_id_seq OWNED BY public.ai_usage_logs.id;


--
-- Name: business_mapping_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business_mapping_profiles (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    detected_sheet_name character varying(200),
    subcategory_key character varying(80),
    detection_method character varying(30) NOT NULL,
    confidence_score numeric(4,3) NOT NULL,
    column_map jsonb NOT NULL,
    ignored_fields jsonb NOT NULL,
    raw_headers jsonb NOT NULL,
    is_confirmed boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.business_mapping_profiles OWNER TO postgres;

--
-- Name: business_mapping_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.business_mapping_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.business_mapping_profiles_id_seq OWNER TO postgres;

--
-- Name: business_mapping_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.business_mapping_profiles_id_seq OWNED BY public.business_mapping_profiles.id;


--
-- Name: businesses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.businesses (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    business_type_key character varying(100) NOT NULL,
    business_name character varying(200) NOT NULL,
    contact_text text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.businesses OWNER TO postgres;

--
-- Name: businesses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.businesses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.businesses_id_seq OWNER TO postgres;

--
-- Name: businesses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.businesses_id_seq OWNED BY public.businesses.id;


--
-- Name: channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channels (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    platform public.platform NOT NULL,
    channel_identifier character varying(200) NOT NULL,
    activation_status character varying(30) NOT NULL,
    is_connected boolean NOT NULL,
    connected_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    contact_id_telegram character varying(200),
    contact_id_bale character varying(200),
    contact_id_eitaa character varying(200),
    phone_telegram character varying(30),
    phone_bale character varying(30),
    phone_eitaa character varying(30)
);


ALTER TABLE public.channels OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.channels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channels_id_seq OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.channels_id_seq OWNED BY public.channels.id;


--
-- Name: customers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.customers (
    id integer NOT NULL,
    telegram_user_id bigint,
    bale_user_id bigint,
    telegram_first_name character varying(100),
    telegram_last_name character varying(100),
    telegram_username character varying(100),
    bale_first_name character varying(100),
    bale_last_name character varying(100),
    bale_username character varying(100),
    first_name character varying(100),
    last_name character varying(100),
    username character varying(100),
    source_platform character varying(20) NOT NULL,
    business_type_key character varying(100),
    eitaa_bot_token character varying(500),
    customer_status public.customerstatus NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    selected_post_preset_id integer
);


ALTER TABLE public.customers OWNER TO postgres;

--
-- Name: customers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.customers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.customers_id_seq OWNER TO postgres;

--
-- Name: customers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.customers_id_seq OWNED BY public.customers.id;


--
-- Name: google_sheet_connections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.google_sheet_connections (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    sheet_url text NOT NULL,
    sheet_id character varying(200) NOT NULL,
    worksheet_name character varying(200) NOT NULL,
    is_active boolean NOT NULL,
    last_sync_at timestamp without time zone,
    last_sync_status character varying(50),
    last_error text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.google_sheet_connections OWNER TO postgres;

--
-- Name: google_sheet_connections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.google_sheet_connections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.google_sheet_connections_id_seq OWNER TO postgres;

--
-- Name: google_sheet_connections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.google_sheet_connections_id_seq OWNED BY public.google_sheet_connections.id;


--
-- Name: post_template_presets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_template_presets (
    id integer NOT NULL,
    business_type_key character varying(100) NOT NULL,
    subcategory_key character varying(80),
    name_fa character varying(200) NOT NULL,
    template_text text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    display_order integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.post_template_presets OWNER TO postgres;

--
-- Name: post_template_presets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.post_template_presets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.post_template_presets_id_seq OWNER TO postgres;

--
-- Name: post_template_presets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.post_template_presets_id_seq OWNED BY public.post_template_presets.id;


--
-- Name: post_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.post_templates (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    template_name character varying(200) NOT NULL,
    title_pattern character varying(500) NOT NULL,
    title_bold boolean NOT NULL,
    body_fields jsonb NOT NULL,
    field_separator character varying(20) NOT NULL,
    skip_if_out_of_stock boolean NOT NULL,
    skip_if_price_zero boolean NOT NULL,
    min_stock integer NOT NULL,
    use_image boolean NOT NULL,
    fallback_image_url text,
    contact_text text,
    static_hashtags jsonb NOT NULL,
    dynamic_hashtags jsonb NOT NULL,
    layout character varying(30) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.post_templates OWNER TO postgres;

--
-- Name: post_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.post_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.post_templates_id_seq OWNER TO postgres;

--
-- Name: post_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.post_templates_id_seq OWNED BY public.post_templates.id;


--
-- Name: posted_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posted_messages (
    id integer NOT NULL,
    product_id integer NOT NULL,
    channel_id integer NOT NULL,
    platform public.platform NOT NULL,
    telegram_message_id bigint,
    telegram_message_ids jsonb NOT NULL,
    last_caption text,
    last_price numeric(18,0),
    last_stock_qty integer,
    status character varying(30) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.posted_messages OWNER TO postgres;

--
-- Name: posted_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posted_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.posted_messages_id_seq OWNER TO postgres;

--
-- Name: posted_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posted_messages_id_seq OWNED BY public.posted_messages.id;


--
-- Name: posting_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posting_settings (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    auto_publish_enabled boolean NOT NULL,
    interval_hours integer NOT NULL,
    posting_start_hour integer NOT NULL,
    posting_end_hour integer NOT NULL,
    auto_ai_description boolean NOT NULL,
    last_post_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    interval_minutes integer
);


ALTER TABLE public.posting_settings OWNER TO postgres;

--
-- Name: posting_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posting_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.posting_settings_id_seq OWNER TO postgres;

--
-- Name: posting_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posting_settings_id_seq OWNED BY public.posting_settings.id;


--
-- Name: product_platform_media; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_platform_media (
    id integer NOT NULL,
    product_id integer NOT NULL,
    platform public.platform NOT NULL,
    file_id character varying(300) NOT NULL,
    media_order integer NOT NULL,
    uploaded_by_customer boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.product_platform_media OWNER TO postgres;

--
-- Name: product_platform_media_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.product_platform_media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_platform_media_id_seq OWNER TO postgres;

--
-- Name: product_platform_media_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.product_platform_media_id_seq OWNED BY public.product_platform_media.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    business_id integer,
    sub_category_key character varying(80),
    sku character varying(80) NOT NULL,
    product_name character varying(250) NOT NULL,
    price numeric(18,0) NOT NULL,
    stock_qty integer NOT NULL,
    is_available boolean NOT NULL,
    description_custom text,
    image_url text,
    specs jsonb NOT NULL,
    publish_status public.productpublishstatus NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ai_description text,
    ai_pros jsonb DEFAULT '[]'::jsonb,
    ai_cons jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscriptions (
    id integer NOT NULL,
    customer_id integer NOT NULL,
    plan_key character varying(50) NOT NULL,
    status public.subscriptionstatus NOT NULL,
    start_at timestamp without time zone NOT NULL,
    end_at timestamp without time zone NOT NULL,
    grace_end_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.subscriptions OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subscriptions_id_seq OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subscriptions_id_seq OWNED BY public.subscriptions.id;


--
-- Name: tutorials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tutorials (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    title character varying(200) NOT NULL,
    category character varying(50) NOT NULL,
    content_type character varying(20) NOT NULL,
    text_content text,
    video_file_id character varying(300),
    video_caption text,
    display_order integer NOT NULL,
    is_active boolean NOT NULL,
    faq_question character varying(300),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tutorials OWNER TO postgres;

--
-- Name: tutorials_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tutorials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tutorials_id_seq OWNER TO postgres;

--
-- Name: tutorials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tutorials_id_seq OWNED BY public.tutorials.id;


--
-- Name: account_link_codes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_link_codes ALTER COLUMN id SET DEFAULT nextval('public.account_link_codes_id_seq'::regclass);


--
-- Name: ai_tokens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_tokens ALTER COLUMN id SET DEFAULT nextval('public.ai_tokens_id_seq'::regclass);


--
-- Name: ai_usage_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_usage_logs ALTER COLUMN id SET DEFAULT nextval('public.ai_usage_logs_id_seq'::regclass);


--
-- Name: business_mapping_profiles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_mapping_profiles ALTER COLUMN id SET DEFAULT nextval('public.business_mapping_profiles_id_seq'::regclass);


--
-- Name: businesses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.businesses ALTER COLUMN id SET DEFAULT nextval('public.businesses_id_seq'::regclass);


--
-- Name: channels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels ALTER COLUMN id SET DEFAULT nextval('public.channels_id_seq'::regclass);


--
-- Name: customers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers ALTER COLUMN id SET DEFAULT nextval('public.customers_id_seq'::regclass);


--
-- Name: google_sheet_connections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_sheet_connections ALTER COLUMN id SET DEFAULT nextval('public.google_sheet_connections_id_seq'::regclass);


--
-- Name: post_template_presets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_template_presets ALTER COLUMN id SET DEFAULT nextval('public.post_template_presets_id_seq'::regclass);


--
-- Name: post_templates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_templates ALTER COLUMN id SET DEFAULT nextval('public.post_templates_id_seq'::regclass);


--
-- Name: posted_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posted_messages ALTER COLUMN id SET DEFAULT nextval('public.posted_messages_id_seq'::regclass);


--
-- Name: posting_settings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_settings ALTER COLUMN id SET DEFAULT nextval('public.posting_settings_id_seq'::regclass);


--
-- Name: product_platform_media id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_platform_media ALTER COLUMN id SET DEFAULT nextval('public.product_platform_media_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions ALTER COLUMN id SET DEFAULT nextval('public.subscriptions_id_seq'::regclass);


--
-- Name: tutorials id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tutorials ALTER COLUMN id SET DEFAULT nextval('public.tutorials_id_seq'::regclass);


--
-- Data for Name: account_link_codes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.account_link_codes (id, customer_id, link_code, expires_at, is_used, failed_attempts, created_at) FROM stdin;
7	5	219879	2026-08-30 20:52:04.232394	t	0	2026-08-30 20:47:04.235842
\.


--
-- Data for Name: ai_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ai_tokens (id, customer_id, source, total_amount, used_amount, remaining_amount, expires_at, created_at) FROM stdin;
5	5	MONTHLY	100	0	100	2026-09-04 23:01:22.854809	2026-08-28 23:01:22.854809
3	1	MONTHLY	100	24	76	2026-09-22 21:46:26.066859	2026-08-23 21:46:26.066859
7	5	MONTHLY	100	0	100	2026-10-03 08:28:30.936235	2026-09-03 08:28:30.936235
6	5	MONTHLY	100	0	100	2026-09-04 23:03:35.058727	2026-08-28 23:03:35.058727
4	4	MONTHLY	100	0	100	2026-09-22 22:23:42.400292	2026-08-23 22:23:42.400292
1	1	MONTHLY	10	10	0	2026-09-22 00:53:28.391367	2026-08-23 00:53:28.391367
\.


--
-- Data for Name: ai_usage_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ai_usage_logs (id, customer_id, product_id, usage_type, tokens_used, model_used, accepted, raw_response, created_at) FROM stdin;
19	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:03:24.590325
20	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:04:36.370566
21	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:04:46.10738
14	5	96	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-30 20:52:01.67191
15	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 09:59:30.256
16	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 09:59:52.611055
17	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:01:32.779056
18	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:01:55.518311
22	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:09:40.607528
23	1	84	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:10:01.151451
24	1	85	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:43:37.724377
25	1	85	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:43:55.930135
26	1	85	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:44:19.85043
27	1	85	improve	1	google/gemma-4-26b-a4b-it:free	f	D: مایکروسافت سرفیس پرو ۵ با قابلیت اتصال LTE، ترکیبی قدرتمند از تبلت و لپتاپ است. این دستگاه با نمایشگر باکیفیت 2K و پردازنده Core i5، گزینه‌ای ایده‌آل برای جابه‌جایی و کارهای اداری محسوب می‌شود.\nP1: نمایشگر باکیفیت 2K لمسی\nP2: قابلیت اتصال اینترنت LTE\nP3: وزن بسیار سبک و کم‌حجم\nP4: سرعت بالای حافظه SSD\nP5: عملکرد مناسب در کارهای اداری\nN1: صفحه نمایش دارای ترک\nN2: گرافیک ضعیف برای بازی	2026-08-31 10:46:04.718244
28	1	85	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:46:27.122423
29	1	85	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:46:47.14864
30	1	86	failed	0	google/gemma-4-26b-a4b-it:free	f	محدودیت درخواست - چند لحظه صبر کنید	2026-08-31 10:48:39.408763
31	1	86	failed	0	deepseek/deepseek-v4-flash-0731	f	پاسخ خالی از سرور هوش مصنوعی	2026-08-31 10:51:24.765055
32	1	85	failed	0	deepseek/deepseek-v4-flash-0731	f	پاسخ AI قابل پردازش نیست	2026-08-31 10:52:01.06454
33	1	85	failed	0	openai/gpt-oss-120b	f	پاسخ خالی از سرور هوش مصنوعی	2026-08-31 10:54:04.288727
34	1	84	failed	0	openai/gpt-oss-120b	f	پاسخ خالی از سرور هوش مصنوعی	2026-08-31 10:58:53.343055
35	1	84	failed	0	openai/gpt-oss-120b	f	پاسخ خالی از سرور هوش مصنوعی	2026-08-31 11:01:57.969343
36	1	87	generate	1	openai/gpt-oss-120b	f	D: Zbook Fury G8 ایستگاه کاری پرقدرت برای مهندسان، طراحان و متخصصان گرافیک است که با پردازنده i7‑11850H و کارت گرافیک Nvidia Quadro RTX 5000 رندرینگ و شبیه‌سازی سنگین را به حداکثر می‌رساند. مناسب پردازش داده‌های بزرگ.  \nP1: پردازنده i7‑11850H قدرتمند  \nP2: کارت گرافیک Quadro RTX 5000  \nP3: صفحه نمایش 17.3 اینچ IPS  \nP4: رم 16 GB DDR4 سرعت‌بالا  \nP5: حافظه SSD 512 GB سریع  \nN1: قیمت بالا برای کاربران عادی  \nN2: وزن نسبتاً سنگین برای حمل‌دستگاهی	2026-08-31 11:05:56.766279
37	1	86	generate	1	google/gemma-3-12b-it	f	D: ThinkPad T540P یک لپتاپ صنعتی و قدرتمند برای انجام کارهای حرفه‌ای و سنگین است. با پردازنده قوی و کارت گرافیک مجزا، برای مهندسان، طراحان و برنامه‌نویسان ایده‌آل است. صفحه نمایش مات FHD، تجربه کاربری راحت‌تری را ارائه می‌دهد.\nP1: پردازنده Intel Core i5 نسل چهارم\nP2: حافظه SSD با ظرفیت ۲۵۶ گیگابایت\nP3: کارت گرافیک Nvidia GT730M\nP4: ۸ گیگابایت رم DDR3\nP5: صفحه نمایش مات ۱۵.۶ اینچی\nN1: عمر باتری محدود\nN2: کارت گرافیک قدیمی	2026-08-31 11:08:03.415778
38	1	86	generate	1	google/gemma-3-12b-it	f	D: ThinkPad T540P یک لپتاپ صنعتی و قدرتمند برای انجام کارهای حرفه‌ای و سنگین مانند برنامه‌نویسی و طراحی است. با پردازنده قوی و کارت گرافیک مجزا، عملکرد مناسبی را ارائه می‌دهد. صفحه نمایش مات FHD آن برای کار در محیط‌های روشن ایده‌آل است.\nP1: پردازنده Intel Core i5 نسل چهارم\nP2: حافظه SSD با ظرفیت ۲۵۶ گیگابایت\nP3: کارت گرافیک Nvidia GT730M\nP4: ۸ گیگابایت رم DDR3\nP5: صفحه نمایش مات FHD\nN1: عمر باتری محدود\nN2: وزن نسبتاً زیاد	2026-08-31 11:08:10.998457
39	1	86	generate	1	google/gemma-3-12b-it	t	D: ThinkPad T540P یک لپتاپ صنعتی قدرتمند برای انجام کارهای سنگین و برنامه‌نویسی است. با پردازنده قوی و کارت گرافیک مجزا، برای مهندسان و طراحان مناسب است. صفحه نمایش مات FHD، تجربه کاربری راحت‌تری ارائه می‌دهد.\nP1: پردازنده Intel Core i5 نسل چهارم\nP2: حافظه SSD 256 گیگابایتی\nP3: کارت گرافیک Nvidia GT730M\nP4: 8 گیگابایت رم DDR3\nP5: صفحه نمایش مات 15.6 اینچی\nN1: عمر باتری محدود\nN2: کارت گرافیک نسبتاً قدیمی	2026-08-31 11:08:15.519519
40	1	85	improve	1	google/gemma-3-12b-it	f	D: Surface Pro 5 LTE با صفحه نمایش ترک‌خورده موجود است. این تبلت/لپتاپ 2-در-1 با پردازنده i5 و 8 گیگابایت رم، برای کارهای روزمره و سبک مناسب است. با وجود صفحه آسیب‌دیده، همچنان قابلیت استفاده دارد.\nP1: پردازنده i5 نسل هفتم\nP2: 8 گیگابایت حافظه رم\nP3: 256 گیگابایت حافظه SSD\nP4: قابلیت اتصال LTE\nP5: صفحه نمایش لمسی 2K\nN1: صفحه نمایش دارای ترک\nN2: عمر باتری متوسط	2026-08-31 11:12:43.156352
41	1	85	improve	1	google/gemma-3-12b-it	t	D: Surface Pro 5 LTE با صفحه نمایش ترک‌خورده موجود است. این تبلت/لپتاپ قدرتمند با پردازنده i5 و حافظه SSD، برای کارهای روزمره و سبک مناسب است. با وجود صفحه آسیب‌دیده، همچنان عملکرد خوبی ارائه می‌دهد.\nP1: پردازنده i5 نسل هفتم\nP2: حافظه 8 گیگابایت رم\nP3: حافظه SSD 256 گیگابایتی\nP4: صفحه نمایش 2K لمسی\nP5: قابلیت اتصال LTE\nN1: صفحه نمایش دارای ترک\nN2: عمر باتری محدود	2026-08-31 11:13:12.951604
42	1	89	generate	1	google/gemma-3-12b-it	t	D: لپتاپ 2233SN سامسونگ، یک انتخاب ایده‌آل برای دانشجویان و کاربران خانگی است که به دنبال یک دستگاه با کارایی مناسب و برند معتبر هستند. این مدل با قابلیت‌های متنوع، برای انجام کارهای روزمره و سرگرمی طراحی شده است.\nP1: کیفیت ساخت قابل قبول سامسونگ\nP2: صفحه نمایش با رزولوشن مناسب\nP3: وزن نسبتاً سبک برای حمل\nP4: امکانات ارتباطی کامل\nP5: قیمت رقابتی در بازار\nN1: مشخصات فنی پایه برای پردازش\nN2: عدم وجود کارت گرافیک مجزا	2026-08-31 18:37:47.971721
43	1	121	generate	1	google/gemma-3-12b-it	t	D: لپتاپ Zbook Fury G8 یک ایستگاه کاری قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، به راحتی کارهای سنگین را انجام می‌دهد. نمایشگر بزرگ و باکیفیت، تجربه‌ی بصری عالی را فراهم می‌کند.\n\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: حافظه رم ۱۶GB DDR4 برای اجرای همزمان برنامه‌ها\nF3: حافظه SSD با ظرفیت ۵۱۲GB برای سرعت بالا\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶GB حافظه\nF5: نمایشگر ۱۷.۳ اینچی FHD IPS با کیفیت تصویر عالی\nF6: دارای پورت‌های Thunderbolt 4 برای اتصال سریع\nF7: پورت LAN برای اتصال با سیم به شبکه\nF8: دارای پورت HDMI برای اتصال به نمایشگر خارجی\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: کیبورد با نور پس‌زمینه برای کار در محیط‌های کم نور\nF11: تشخیص چهره با وب‌کم داخلی\nF12: وزن ۲.۳۵ کیلوگرم، قابل حمل برای استفاده‌ی حرفه‌ای\n\nN1: عدم وجود قابلیت LTE\nN2: عدم پشتیبانی از قلم لمسی	2026-09-02 10:25:22.510193
44	1	121	generate	1	google/gemma-3-12b-it	t	D: لپتاپ Zbook Fury G8 یک ایستگاه کاری قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای کارهای سنگین و خلاقانه ایده‌آل است. حافظه گرافیک 16 گیگابایتی RTX 5000 عملکرد بی‌نظیری ارائه می‌دهد.\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: 16 گیگابایت حافظه رم DDR4\nF3: حافظه SSD با ظرفیت 512 گیگابایت\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با 16 گیگابایت حافظه\nF5: صفحه نمایش 17.3 اینچی FHD IPS با کیفیت تصویر بالا\nF6: دارای پورت‌های DisplayPort و HDMI برای اتصال مانیتور خارجی\nF7: شبکه LAN با سرعت بالا برای اتصال پایدار\nF8: وجود پورت Thunderbolt برای انتقال سریع داده\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: صفحه کلید با نور پس‌زمینه برای کار در محیط‌های کم نور\nF11: تشخیص چهره با دوربین وب‌کم\nF12: وزن 2.35 کیلوگرم\nN1: عدم وجود قابلیت LTE\nN2: عدم پشتیبانی از قلم لمسی	2026-09-02 10:56:03.495224
45	1	121	generate	1	google/gemma-3-12b-it	f	D: لپتاپ Zbook Fury G8 یک ایستگاه کاری قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، عملکرد بی‌نظیری در کارهای سنگین ارائه می‌دهد. این لپتاپ با صفحه نمایش بزرگ و باکیفیت، تجربه‌ای عالی برای کار و خلاقیت فراهم می‌کند.\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: ۱۶ گیگابایت حافظه رم DDR4 با سرعت بالا\nF3: درایو SSD با ظرفیت ۵۱۲ گیگابایت\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶ گیگابایت حافظه\nF5: صفحه نمایش ۱۷.۳ اینچی FHD IPS با کیفیت تصویر عالی\nF6: دارای پورت‌های DisplayPort و HDMI برای اتصال به مانیتور\nF7: اتصال شبکه LAN با سرعت بالا\nF8: پشتیبانی از Thunderbolt برای انتقال سریع داده\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: کیبورد با نور پس زمینه برای کار در محیط‌های کم نور\nF11: تشخیص چهره با وب‌کم\nF12: عمر باتری تا ۷ ساعت\nN1: وزن نسبتاً زیاد (۲.۳۵ کیلوگرم)\nN2: عدم وجود درایو DVD-RW	2026-09-02 11:09:04.419623
46	1	121	generate	1	google/gemma-3-12b-it	f	D: Zbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، عملکرد بی‌نظیری در اجرای برنامه‌های سنگین ارائه می‌دهد. این لپتاپ با صفحه نمایش بزرگ و باکیفیت، تجربه کاربری حرفه‌ای را تضمین می‌کند.\n\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: حافظه رم ۱۶GB DDR4 برای اجرای همزمان برنامه‌ها\nF3: حافظه ذخیره‌سازی ۵۱۲GB SSD برای سرعت بالا\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶GB حافظه\nF5: صفحه نمایش ۱۷.۳ اینچی FHD IPS با کیفیت تصویر بالا\nF6: دارای پورت‌های Thunderbolt 4 برای اتصال سریع\nF7: پورت LAN برای اتصال شبکه‌ای پایدار\nF8: وب‌کم با قابلیت تشخیص چهره\nF9: کیبورد با نور پس‌زمینه برای کار در محیط‌های کم نور\nF10: حسگر اثر انگشت برای امنیت بیشتر\nF11: دارای پورت‌های USB متنوع\nF12: عمر باتری ۷ ساعته برای استفاده طولانی مدت\n\nN1: وزن نسبتاً زیاد (۲.۳۵ کیلوگرم)\nN2: عدم وجود درایو DVD-RW	2026-09-02 11:12:57.255283
47	1	121	generate	1	google/gemma-3-12b-it	t	D: Zbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای کارهای سنگین و محاسبات پیچیده ایده‌آل است. صفحه نمایش بزرگ و باکیفیت، تجربه بصری بی‌نظیری را ارائه می‌دهد.\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: ۱۶ گیگابایت رم DDR4 برای اجرای همزمان برنامه‌ها\nF3: حافظه SSD با ظرفیت ۵۱۲ گیگابایت با سرعت بالا\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶ گیگابایت حافظه\nF5: صفحه نمایش ۱۷.۳ اینچی FHD IPS با کیفیت تصویر عالی\nF6: پورت‌های Thunderbolt برای اتصال دستگاه‌های سریع\nF7: دارای پورت LAN برای اتصال با سیم\nF8: وب‌کم با قابلیت تشخیص چهره (Facial Recognition)\nF9: کیبورد با نور پس زمینه (Backlit Keyboard)\nF10: حسگر اثر انگشت (Fingerprint) برای امنیت بیشتر\nF11: دارای پورت‌های USB متعدد\nF12: عمر باتری تا ۷ ساعت\nN1: وزن نسبتاً زیاد (۲.۳۵ کیلوگرم)\nN2: عدم وجود درایو DVD-RW	2026-09-02 11:26:16.150744
48	1	122	generate	1	google/gemma-3-12b-it	t	D: لپتاپ ProBook 650 G1 یک گزینه مناسب برای کاربران حرفه‌ای و دانشجویان است که به دنبال یک دستگاه قابل اعتماد و با کارایی برای انجام وظایف روزمره و محاسبات متوسط هستند. این لپتاپ با پردازنده Intel Core i5 و هارد درایو 500 گیگابایتی، عملکرد قابل قبولی را ارائه می‌دهد.\n\nF1: پردازنده Intel Core i5-4300M برای کارهای روزمره\nF2: حافظه رم 8 گیگابایت برای اجرای همزمان برنامه‌ها\nF3: هارد درایو 500 گیگابایتی برای ذخیره‌سازی حجم زیادی از داده\nF4: صفحه نمایش 15.6 اینچی HD برای دیدن راحت محتوا\nF5: پورت DisplayPort برای اتصال به مانیتورهای خارجی\nF6: پورت LAN برای اتصال به شبکه‌های سیمی\nF7: درایو DVD-RW برای خواندن و نوشتن دیسک‌های نوری\nF8: پنج پورت USB برای اتصال انواع دستگاه‌های جانبی\nF9: وزن 2.32 کیلوگرم، نسبتاً قابل حمل\nF10: عمر باتری تا 5 ساعت در استفاده معمولی\nF11: طراحی مقاوم و بادوام\nF12: مناسب برای استفاده‌های اداری و تحصیلی\n\nN1: گرافیک مجتمع Intel\nN2: عدم وجود صفحه نمایش لمسی	2026-09-02 11:29:30.495263
49	1	124	generate	1	google/gemma-3-12b-it	t	D: ThinkPad T540P یک لپتاپ قدرتمند و بادوام برای متخصصان و کاربران حرفه‌ای است که به دنبال عملکرد بالا و قابلیت اطمینان می‌باشند. این لپتاپ با پردازنده Intel Core i5 و کارت گرافیک Nvidia، برای انجام کارهای سنگین و اجرای برنامه‌های کاربردی مناسب است. صفحه نمایش مات FHD با کیفیت، تجربه بصری راحتی را ارائه می‌دهد.\n\nF1: پردازنده Intel Core i5-4300M برای عملکرد مناسب\nF2: ۸ گیگابایت رم DDR3 برای اجرای همزمان برنامه‌ها\nF3: حافظه SSD ۲۵۶ گیگابایتی برای سرعت بالا در بارگذاری\nF4: کارت گرافیک Nvidia GT730M با ۱ گیگابایت حافظه\nF5: صفحه نمایش ۱۵.۶ اینچی FHD با روکش مات\nF6: پورت DisplayPort برای اتصال به مانیتورهای خارجی\nF7: درایو DVD-RW برای خواندن و نوشتن دیسک\nF8: ۴ پورت USB برای اتصال دستگاه‌های مختلف\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: وزن ۲.۴۱ کیلوگرم، قابل حمل در حد متوسط\nF11: پشتیبانی از قلم (Pen Support) برای یادداشت‌برداری\nF12: کیبورد با نور پس زمینه ندارد\n\nN1: عمر باتری محدود (حدود ۲ ساعت)\nN2: عدم وجود پورت HDMI	2026-09-02 19:16:38.011128
50	1	76	generate	1	google/gemma-3-12b-it	t	D: ProBook 650 G8 یک لپتاپ تجاری قدرتمند برای متخصصان و کاربران حرفه‌ای است که به دنبال ترکیبی از عملکرد، امنیت و قابلیت حمل هستند. پردازنده نسل یازدهم Intel Core i5 و حافظه SSD سریع، تجربه کاربری روانی را ارائه می‌دهند. طراحی مقاوم و ویژگی‌های امنیتی پیشرفته، این لپتاپ را برای استفاده در محیط‌های کاری مختلف ایده‌آل می‌کند.\nF1: پردازنده Intel Core i5-1145G7 نسل یازدهم\nF2: حافظه ۸ گیگابایت DDR4\nF3: حافظه داخلی ۲۵۶ گیگابایت SSD\nF4: صفحه نمایش ۱۵.۶ اینچی Full HD (1920x1080)\nF5: گرافیک مجتمع Intel Iris Xe Graphics\nF6: پورت Thunderbolt 4 برای اتصال سریع\nF7: دارای پورت‌های USB 3.0 متعدد\nF8: حسگر اثر انگشت برای امنیت بیشتر\nF9: شبکه LAN با سرعت بالا\nF10: عمر باتری تا ۶ ساعت\nF11: وزن سبک ۱.۷۴ کیلوگرم\nF12: طراحی مقاوم و بادوام\nN1: عدم وجود درایو DVD-RW\nN2: عدم پشتیبانی از صفحه نمایش لمسی	2026-09-02 19:18:09.277558
51	1	76	generate	1	google/gemma-3-12b-it	t	D: Probook 650 G8 یک لپتاپ تجاری قدرتمند است که برای متخصصان و کاربران حرفه‌ای طراحی شده است. این لپتاپ با پردازنده نسل یازدهم اینتل و حافظه SSD سریع، عملکردی عالی برای کارهای روزمره و سنگین ارائه می‌دهد. ویژگی برجسته آن، وجود پورت Thunderbolt 4 است.\n\nF1: پردازنده Intel Core i5-1145G7 نسل یازدهم\nF2: حافظه رم ۸ گیگابایت DDR4\nF3: حافظه داخلی ۲۵۶ گیگابایت SSD\nF4: صفحه نمایش ۱۵.۶ اینچی با رزولوشن FHD (1920x1080)\nF5: کارت گرافیک Intel Iris Xe Graphics\nF6: پورت Thunderbolt 4 برای اتصال دستگاه‌های سریع\nF7: دارای پورت HDMI برای اتصال به نمایشگر خارجی\nF8: شبکه LAN با سرعت بالا برای اتصال سیمی\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: وزن سبک ۱.۷۴ کیلوگرم برای حمل آسان\nF11: گرید A++ نشان‌دهنده کیفیت بالای محصول\nF12: سه پورت USB برای اتصال دستگاه‌های جانبی\n\nN1: عدم وجود درایو DVD-RW\nN2: فاقد قابلیت پشتیبانی از قلم لمسی	2026-09-03 00:04:38.639652
52	1	123	improve	1	google/gemma-3-12b-it	t	D: Surface Pro 5، یک تبلت/لپتاپ ۲-در-۱ قدرتمند با پردازنده نسل هفتم اینتل و حافظه SSD سریع. این دستگاه با امکان اتصال LTE و همراه داشتن کیبورد بلوتوثی، یک ابزار ایده‌آل برای کارهای سیار و بهره‌وری در هر مکانی است.\n\nF1: پردازنده Intel Core i5-7200U نسل هفتم\nF2: ۸ گیگابایت حافظه رم DDR4\nF3: ۲۵۶ گیگابایت حافظه SSD سریع\nF4: صفحه نمایش لمسی ۲K با کیفیت بالا (12.5 اینچ)\nF5: اتصال LTE برای اینترنت پرسرعت در هر مکان\nF6: وزن سبک و قابل حمل (۰.۷۷ کیلوگرم)\nF7: سیستم عامل ویندوز 10 Pro\nF8: گرافیک مجتمع Intel HD Graphics 620\nF9: پورت USB 3.0 برای انتقال سریع داده\nF10: دوربین جلو و عقب با کیفیت مناسب\nF11: بلندگوهای استریو با صدای فراگیر\nF12: پشتیبانی از قلم Surface Pen (فروش جداگانه)\n\nN1: عمر باتری متوسط\nN2: پورت‌های محدود	2026-09-03 00:10:41.165811
53	1	124	generate	1	google/gemma-3-12b-it	t	D: ThinkPad T540P یک لپتاپ قدرتمند و بادوام برای متخصصان و کاربران حرفه‌ای است که به دنبال عملکرد بالا در یک دستگاه قابل حمل هستند. این لپتاپ با پردازنده قوی و کارت گرافیک مجزا، برای انجام کارهای محاسباتی سنگین و اجرای برنامه‌های حرفه‌ای مناسب است. صفحه نمایش مات FHD آن، تجربه بصری راحت‌تری را ارائه می‌دهد.\n\nF1: پردازنده Intel Core i5-4300M با عملکرد مناسب\nF2: حافظه رم 8GB DDR3 برای اجرای همزمان برنامه‌ها\nF3: درایو SSD 256GB با سرعت بالا برای بوت و اجرای سریع\nF4: کارت گرافیک NVIDIA GeForce GT 730M با 1GB حافظه\nF5: صفحه نمایش 15.6 اینچی با رزولوشن FHD و روکش مات\nF6: پورت DisplayPort برای اتصال به نمایشگرهای خارجی\nF7: پورت LAN (Gigabit Ethernet) برای اتصال با سیم\nF8: درایو DVD-RW برای خواندن و نوشتن دیسک\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: پشتیبانی از قلم (Pen Support) برای یادداشت‌برداری و طراحی\nF11: چهار پورت USB برای اتصال دستگاه‌های مختلف\nF12: وزن نسبتاً سبک 2.41 کیلوگرم\n\nN1: عمر باتری محدود (2 ساعت)\nN2: عدم وجود پورت HDMI	2026-09-03 06:03:02.827537
54	1	124	generate	1	google/gemma-3-12b-it	t	D: ThinkPad T540P یک لپتاپ قدرتمند و بادوام برای متخصصان و کاربران حرفه‌ای است که به دنبال عملکرد بالا در یک بدنه مقاوم می‌باشند. این مدل با پردازنده Intel Core i5 و گرافیک Nvidia، برای کارهای محاسباتی سنگین و برنامه‌های کاربردی مختلف مناسب است. صفحه نمایش مات Full HD آن، تجربه بصری راحت و بدون بازتاب را فراهم می‌کند.\n\nF1: پردازنده Intel Core i5-4300M\nF2: حافظه رم 8GB DDR3\nF3: حافظه SSD با ظرفیت 256GB\nF4: کارت گرافیک Nvidia GT730M با 1GB حافظه\nF5: صفحه نمایش 15.6 اینچی Full HD Matte\nF6: درایو نوری DVD-RW\nF7: پورت DisplayPort برای اتصال مانیتور خارجی\nF8: چهار پورت USB برای اتصال دستگاه‌های جانبی\nF9: حسگر اثر انگشت برای امنیت بیشتر\nF10: پشتیبانی از قلم نوری (Pen Support)\nF11: وزن نسبتاً سبک 2.41 کیلوگرم\nF12: کیبورد با نور پس زمینه ندارد\n\nN1: عمر باتری محدود (2 ساعت)\nN2: عدم وجود پورت HDMI	2026-09-03 06:08:06.134302
55	1	87	generate	1	google/gemma-3-12b-it	t	D: Zbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای اجرای برنامه‌های سنگین و کارهای خلاقانه ایده‌آل است. عملکرد بی‌نظیر و قابلیت اطمینان بالا، آن را به انتخابی مناسب برای محیط‌های حرفه‌ای تبدیل می‌کند.\nF1: پردازنده Intel Core i7-11850H نسل یازدهم\nF2: 16 گیگابایت حافظه رم DDR4 با سرعت بالا\nF3: حافظه داخلی 512 گیگابایت SSD NVMe\nF4: کارت گرافیک Nvidia Quadro RTX 5000 با 16GB حافظه\nF5: نمایشگر 17.3 اینچی FHD IPS با کیفیت بالا\nF6: پنل IPS با رنگ‌های دقیق و زنده\nF7: سیستم خنک‌کننده پیشرفته برای عملکرد پایدار\nF8: بدنه مقاوم و مستحکم با طراحی صنعتی\nF9: پورت‌های متنوع شامل USB-C، Thunderbolt و HDMI\nF10: کیبورد با نور پس‌زمینه برای کار در محیط‌های کم نور\nF11: پشتیبانی از فناوری‌های امنیتی پیشرفته\nF12: مناسب برای رندرینگ، شبیه‌سازی و مدل‌سازی سه‌بعدی\nN1: وزن نسبتاً زیاد\nN2: عمر باتری محدود تحت بار سنگین	2026-09-03 06:10:35.00112
56	1	83	improve	1	google/gemma-3-12b-it	f	D: این Surface Laptop 3 با پردازنده قدرتمند i7 و حافظه رم 16 گیگابایتی، تجربه‌ای روان و سریع را برای کارهای روزمره و حرفه‌ای ارائه می‌دهد. با وجود صفحه نمایش لمسی 2K و قلم هوشمند، امکان خلق ایده‌های نو و بهره‌وری بیشتر را خواهید داشت. توجه داشته باشید که این دستگاه دارای صفحه نمایش با ترک جزئی است.\nF1: پردازنده نسل دهم Intel Core i7-1065G7\nF2: حافظه رم 16 گیگابایت DDR4\nF3: حافظه SSD با ظرفیت 256 گیگابایت\nF4: صفحه نمایش لمسی 13.3 اینچی با رزولوشن 2K\nF5: پشتیبانی از قلم Surface Pen\nF6: دارای پورت Thunderbolt 4\nF7: صفحه کلید با نور پس‌زمینه\nF8: تشخیص چهره با Windows Hello\nF9: عمر باتری تا 5 ساعت\nF10: وزن سبک 1.54 کیلوگرم\nF11: یک پورت USB 3.0\nF12: گرافیک مجتمع Intel Iris Plus Graphics\nN1: فاقد پورت LAN\nN2: عدم وجود درگاه HDMI	2026-09-03 06:35:58.661514
57	1	65	generate	1	google/gemma-3-12b-it	t	D: MacBook Air 2017 یک لپتاپ سبک و قابل حمل برای دانشجویان، کارمندان و کاربرانی است که به دنبال عملکرد روزمره و باتری طولانی‌مدت هستند. پردازنده i5 و حافظه SSD آن، تجربه‌ای سریع و روان را ارائه می‌دهد. طراحی باریک و وزن کم آن، حمل و نقل آسان را ممکن می‌سازد.\n\nF1: پردازنده Intel Core i5 نسل هفتم\nF2: حافظه رم ۸ گیگابایت DDR3\nF3: حافظه داخلی ۱۲۸ گیگابایت SSD\nF4: صفحه نمایش ۱۴ اینچی با رزولوشن FHD (1920x1080)\nF5: گرافیک مجتمع Intel HD Graphics 6000\nF6: سیستم عامل macOS\nF7: طراحی باریک و سبک (فقط ۱.۲۵ کیلوگرم)\nF8: باتری با طول عمر بالا (تا ۱۲ ساعت)\nF9: پورت‌های Thunderbolt 3\nF10: اسپیکرهای استریو\nF11: وب‌کم FaceTime HD\nF12: حسگر اثر انگشت Touch ID\n\nN1: عدم وجود پورت‌های USB-A\nN2: گرافیک مجتمع برای بازی‌های سنگین محدود	2026-09-03 06:38:11.536234
58	1	89	improve	1	google/gemma-3-12b-it	t	D: لپتاپ 2233SN سامسونگ، گزینه‌ای مقرون‌به‌صرفه برای انجام امور روزمره، تکالیف دانشجویی و سرگرمی‌های سبک است. با تکیه بر کیفیت ساخت سامسونگ و صفحه نمایش باکیفیت، تجربه‌ای قابل قبول را برای کاربران خانگی و دانش‌آموزان ارائه می‌دهد. این لپتاپ با وزن نسبتاً سبک و امکانات ارتباطی کامل، برای استفاده‌های متغیر مناسب است.\nF1: صفحه نمایش 21.5 اینچی LCD\nF2: رزولوشن Full HD (1920x1080)\nF3: نرخ تازه‌سازی 60 هرتز\nF4: کیفیت تصویر مناسب برای محتوای استاندارد\nF5: بدنه مقاوم و بادوام\nF6: وزن سبک برای حمل و نقل آسان\nF7: پورت‌های متنوع (USB، HDMI، و غیره)\nF8: وب‌کم و میکروفون داخلی\nF9: بلندگوهای استریو\nF10: پشتیبانی از Wi-Fi و بلوتوث\nF11: سیستم عامل از پیش نصب شده (ویندوز)\nF12: باتری با طول عمر متوسط\nN1: پردازنده گرافیکی یکپارچه\nN2: حافظه و رم محدود	2026-09-03 06:43:11.892659
59	1	64	improve	1	google/gemma-3-12b-it	t	D: لپتاپ 1215N Mini از ایسوس، یک گزینه سبک و مقرون‌به‌صرفه برای کارهای روزمره و دانشجویی است. این مدل با وجود ابعاد کوچک، امکان اتصال به شبکه را فراهم می‌کند و برای حمل و نقل آسان طراحی شده است. توجه داشته باشید که این محصول فاقد باتری است.\nF1: پردازنده Intel Atom D525 برای کارهای سبک\nF2: رم 6 گیگابایت برای اجرای همزمان برنامه‌ها\nF3: هارد دیسک 500 گیگابایتی فضای ذخیره‌سازی\nF4: گرافیک مجتمع Intel برای نمایش تصاویر\nF5: صفحه نمایش HD با کیفیت مناسب\nF6: پورت شبکه LAN برای اتصال سیمی\nF7: خروجی HDMI برای اتصال به نمایشگر خارجی\nF8: سه پورت USB برای اتصال دستگاه‌های جانبی\nF9: وزن سبک 1.5 کیلوگرمی برای حمل آسان\nF10: طراحی فشرده و قابل حمل\nF11: مناسب برای کارهای اداری و دانشجویی\nF12: سیستم عامل سازگار با انواع نرم‌افزار\nN1: عدم وجود باتری\nN2: گرافیک نه برای بازی‌های سنگین	2026-09-03 06:54:37.67285
60	1	64	improve	1	google/gemma-3-12b-it	t	D: لپتاپ 1215N Mini ایسوس، یک گزینه سبک و قابل حمل برای کارهای روزمره و دانشجویی است. با وجود عدم باتری، این مدل برای استفاده در محیط‌های ثابت مانند دفتر کار یا خانه ایده‌آل است و امکان اتصال به برق را به صورت مداوم فراهم می‌کند. این لپتاپ با پردازنده اتم و هارددیسک 500 گیگابایتی، نیازهای اساسی شما را برآورده می‌کند.\nF1: پردازنده Intel Atom D525 برای کاربری سبک\nF2: رم 6 گیگابایت برای اجرای همزمان برنامه‌ها\nF3: هارددیسک 500 گیگابایتی فضای ذخیره‌سازی کافی\nF4: صفحه نمایش HD با کیفیت تصویر مناسب\nF5: پورت LAN برای اتصال به شبکه سیمی\nF6: خروجی HDMI برای اتصال به نمایشگر خارجی\nF7: سه پورت USB برای اتصال لوازم جانبی\nF8: وزن سبک 1.5 کیلوگرمی برای حمل آسان\nF9: طراحی فشرده و جمع‌وجور\nF10: مناسب برای کارهای متنی و وب‌گردی\nF11: سیستم عامل ویندوز (پیش‌فرض)\nF12: قابلیت ارتقاء رم (بررسی با سازنده)\nN1: عدم وجود باتری\nN2: گرافیک مجتمع اینتل	2026-09-03 07:28:03.792913
61	1	65	generate	1	google/gemma-3-12b-it	t	D: MacBook Air 2017 یک لپتاپ سبک و قابل حمل برای دانشجویان، کارمندان و کاربرانی است که به دنبال یک دستگاه با عملکرد مناسب برای کارهای روزمره و بهره‌وری هستند. این مدل با پردازنده Intel i5 و حافظه SSD، تجربه‌ای سریع و روان را ارائه می‌دهد.\n\nF1: پردازنده Intel Core i5 نسل هفتم\nF2: ۸ گیگابایت حافظه رم DDR3\nF3: حافظه داخلی ۱۲۸ گیگابایت SSD\nF4: صفحه نمایش ۱۴ اینچی با رزولوشن FHD\nF5: گرافیک مجتمع Intel HD Graphics 6000\nF6: طراحی باریک و سبک با وزن کم\nF7: سیستم عامل macOS\nF8: عمر باتری مناسب برای استفاده روزانه\nF9: پورت‌های Thunderbolt 3 برای اتصال سریع\nF10: بلندگوهای استریو با کیفیت\nF11: کیبورد با نور پس‌زمینه\nF12: حسگر اثر انگشت Touch ID\n\nN1: عدم وجود پورت‌های USB-A\nN2: حافظه داخلی نسبتاً کم	2026-09-03 07:28:53.086548
\.


--
-- Data for Name: business_mapping_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.business_mapping_profiles (id, customer_id, detected_sheet_name, subcategory_key, detection_method, confidence_score, column_map, ignored_fields, raw_headers, is_confirmed, created_at, updated_at) FROM stdin;
1	1	clothing	clothing	auto_exact	1.000	{"sku": 0, "size": 3, "brand": 2, "color": 6, "price": 4, "stock": 5, "material": 7, "image_url": 9, "description": 8, "product_name": 1}	[]	["کد محصول", "نام محصول", "برند", "سایزبندی", "قیمت", "موجودی", "رنگ‌بندی", "جنس", "توضیحات", "لینک عکس"]	t	2026-08-26 20:14:36.415801	2026-08-26 20:14:36.409628
\.


--
-- Data for Name: businesses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.businesses (id, customer_id, business_type_key, business_name, contact_text, created_at) FROM stdin;
3	4	computer_shop	کسب‌وکار Loco	@Locomoc	2026-08-23 22:22:55.867466
4	5	computer_shop	کسب‌وکار ᵐᵉʰᵈⁱ	@HeMyti	2026-08-26 13:15:31.640255
9	1	computer_shop	کسب‌وکار -Antonio	@Nick_Bri	2026-08-29 08:58:36.215708
11	6	clothing_shop	کسب‌وکار 𝑵𝒂𝒈𝒉𝒎𝒆	@Naghme_pv	2026-09-03 00:08:07.35737
\.


--
-- Data for Name: channels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.channels (id, customer_id, platform, channel_identifier, activation_status, is_connected, connected_at, created_at, contact_id_telegram, contact_id_bale, contact_id_eitaa, phone_telegram, phone_bale, phone_eitaa) FROM stdin;
5	4	EITAA	11226043	ACTIVE	t	2026-08-30 16:29:00.326731	2026-08-30 16:29:00.326841	\N	\N	\N	\N	\N	\N
6	5	TELEGRAM	@pnxtest	ACTIVE	t	2026-08-30 20:23:25.665084	2026-08-30 20:23:25.665099	\N	\N	\N	\N	\N	\N
7	5	EITAA	11237922	ACTIVE	t	2026-08-30 20:43:39.272128	2026-08-30 20:43:39.272153	\N	\N	\N	\N	\N	\N
8	5	BALE	@pnxtest	ACTIVE	t	2026-08-30 20:53:49.460104	2026-08-30 20:53:49.460121	\N	\N	\N	\N	\N	\N
9	1	TELEGRAM	@testadasdwqfasfvsdvdfc	ACTIVE	t	2026-08-30 21:46:41.173879	2026-08-30 21:46:41.173896	@fasfasfdsada	\N	\N	09102807430	\N	\N
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.customers (id, telegram_user_id, bale_user_id, telegram_first_name, telegram_last_name, telegram_username, bale_first_name, bale_last_name, bale_username, first_name, last_name, username, source_platform, business_type_key, eitaa_bot_token, customer_status, created_at, updated_at, selected_post_preset_id) FROM stdin;
6	8259673711	\N	𝑵𝒂𝒈𝒉𝒎𝒆	\N	Naghme_pv	\N	\N	\N	𝑵𝒂𝒈𝒉𝒎𝒆	\N	Naghme_pv	TELEGRAM	clothing_shop	\N	ACTIVE	2026-09-03 00:07:05.127488	2026-09-03 00:08:07.348598	\N
1	8215541369	1455437359	-Antonio	\N	Nick_Bri	ALI	\N	\N	-Antonio	\N	Nick_Bri	TELEGRAM	computer_shop	gAAAAABqi22KSXg3gNY-rzFzVncC7QpHPFAfVWa-bwzj5YvTL_sSer-yXP3QlrbH-3cCBboz8exNW9eA6ns0kKkEUF2jRVyGh_fq92jaCI9LFqb2DlTxKZtEnLl_Uusome8-ARU_kpUL	ACTIVE	2026-08-23 00:42:03.843438	2026-09-03 06:35:04.876783	2
4	6991820336	\N	Loco	13:52	Locomoc	\N	\N	\N	Loco	13:52	Locomoc	TELEGRAM	computer_shop	gAAAAABqlFO2JturNR6FsYGC_K54k964l0dVxhgVMbwOVB6a865wWF5oCLPcfF0RTO6FBg8uTyQd0L2aUdewPW7GrHkPvlxg2G4gYgTwZAltrRYUMiik5JX26YMgaanTPhXXZsqR8I9o	ACTIVE	2026-08-23 22:22:55.806222	2026-08-30 16:00:54.250561	\N
5	998679924	1296017141	ᵐᵉʰᵈⁱ	\N	HeMyti	Seyed Mahdi	\N	he_myti	ᵐᵉʰᵈⁱ	\N	HeMyti	TELEGRAM	computer_shop	gAAAAABqk8IXp8u9SKsj3pJDadt8BKWNsUC9V-rY09CrQPZYeYkUeoaa70HP72Dp8sPK1kiUp-2eEjydhwKjDZmCGjtOKtpuhKQRORliMBuZTMBuYpf-zrl7_b1XAyC6XV6KwplySoA7	ACTIVE	2026-08-26 13:15:31.581853	2026-08-30 20:47:14.575334	\N
\.


--
-- Data for Name: google_sheet_connections; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.google_sheet_connections (id, customer_id, sheet_url, sheet_id, worksheet_name, is_active, last_sync_at, last_sync_status, last_error, created_at, updated_at) FROM stdin;
3	4	https://docs.google.com/spreadsheets/d/1oF_Id0iFJVFGeuoM0QnmZ3A8u8axOK8Mq0iMbs8ZHO0/edit?usp=sharing	1oF_Id0iFJVFGeuoM0QnmZ3A8u8axOK8Mq0iMbs8ZHO0	multi_sheet	t	2026-08-31 09:24:35.487287	SUCCESS	\N	2026-08-26 15:33:45.695047	2026-08-31 09:24:35.487845
9	1	https://docs.google.com/spreadsheets/d/1H8c5L3GpTP0AMC6lrU3aBrVkYkcuSKWFSsXVsblf9eE/edit?gid=0#gid=0	1H8c5L3GpTP0AMC6lrU3aBrVkYkcuSKWFSsXVsblf9eE	multi_sheet	t	2026-09-04 13:32:29.353402	SUCCESS	\N	2026-08-29 08:58:48.809325	2026-09-04 13:32:29.354251
8	5	https://docs.google.com/spreadsheets/d/1H8c5L3GpTP0AMC6lrU3aBrVkYkcuSKWFSsXVsblf9eE/edit?usp=sharing	1H8c5L3GpTP0AMC6lrU3aBrVkYkcuSKWFSsXVsblf9eE	multi_sheet	t	2026-09-04 13:32:30.423883	SUCCESS	\N	2026-08-29 08:14:46.381235	2026-09-04 13:32:30.42463
\.


--
-- Data for Name: post_template_presets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.post_template_presets (id, business_type_key, subcategory_key, name_fa, template_text, is_active, display_order, created_at, updated_at) FROM stdin;
3	computer_shop	\N	test	{product_name}        \n{sku}               \n{price}                 \n{stock_status}     \n{description_block}    \n{image_url}         \n{contact}            \n{hashtags}           \n\ntest \n\n{brand} \n {cpu}\n  {ram}\n  {storage}\n  {gpu}\n  {screen}\ntuch : {touch_screen}\npen : {pen_support}\n360 :  {x360}\n  {lte}\n  {dvd_rw}\n{backlit_keyboard}\n  {fingerprint}\n  {facial_recognition}\n{hdmi}\n  {dp}\n  {vga_port}\n  {lan}\n  {thunderbolt}\n{usb_ports}\n  {battery_life}\n Grade : {grade}\n  {weight}	t	0	2026-09-02 19:20:28.347352	2026-09-02 23:53:40.193593
1	computer_shop	\N	Default	🖥 {brand} {product_name}\n\n⚡️ پردازنده: {cpu}\n🧠 رم: {ram}\n💾 حافظه: {storage}\n🎮 گرافیک: {gpu}\n📐 صفحه: {screen}\n\n⭐️ {grade}\n\n{ai_description}\n\n{ai_features}\n\n🎯 مناسب برای\n{hashtags}\n\n─────────────────\n💰 قیمت: {price} تومان\n📦 {stock_status}\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 {contact}\n🔄 {update_date}	t	0	2026-09-01 03:07:23.11278	2026-09-02 11:40:45.633069
2	computer_shop	\N	حرفه ای	📄 حرفه ای\n━━━━━━━━━━━━━━━\n🏢 کسب‌وکار: computer_shop\n🗂 زیردسته: همه\n📊 وضعیت: 🟢 فعال\n━━━━━━━━━━━━━━━\n\nمتن قالب:\n🖥 {brand} {product_name}\n\n⚡️ پردازنده: {cpu}\n🧠 رم: {ram}\n💾 حافظه: {storage}\n🎮 گرافیک: {gpu}\n📐 صفحه: {screen}\n\n⭐️ {grade}\n\n📝 توضیحات محصول :\n{ai_description}\n\nقابلیت ها :\n{ai_features}\n\n\n🎯 مناسب برای\n{hashtags}\n\n─────────────────\n💰 قیمت: {price} تومان\n📦 {stock_status}\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 {contact_id} | {phone}\n🔄 {update_date}	t	0	2026-09-02 11:28:31.31071	2026-09-03 07:27:18.823711
\.


--
-- Data for Name: post_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.post_templates (id, customer_id, template_name, title_pattern, title_bold, body_fields, field_separator, skip_if_out_of_stock, skip_if_price_zero, min_stock, use_image, fallback_image_url, contact_text, static_hashtags, dynamic_hashtags, layout, created_at, updated_at) FROM stdin;
1	1	قالب پیش‌فرض	👕 {brand} | {product_name}	t	[{"key": "price", "label": "💰 قیمت", "format": "{value:,} تومان", "enabled": true}, {"key": "specs.color", "label": "🎨 رنگ", "format": "{value}", "enabled": true}, {"key": "specs.size", "label": "📏 سایز", "format": "{value}", "enabled": true}, {"key": "specs.material", "label": "🧶 جنس", "format": "{value}", "enabled": false}, {"key": "stock_qty", "label": "📦 موجودی", "format": "{value} عدد", "enabled": true}, {"key": "description_manual", "label": "📝 توضیحات", "format": "{value}", "enabled": false}]	\n	t	t	1	t	\N	\N	["#پوشاک", "#لباس", "#مد", "#خرید_آنلاین"]	[{"field": "brand", "prefix": "#"}, {"field": "specs.color", "prefix": "#رنگ_"}]	text_with_image	2026-08-26 19:53:01.37008	2026-08-26 19:53:01.370108
2	5	قالب پیش‌فرض	💻 {brand} {product_name}	t	[{"key": "price", "label": "💰 قیمت", "format": "{value:,} تومان", "enabled": true}, {"key": "stock_qty", "label": "📦 موجودی", "format": "{value} عدد", "enabled": true}, {"key": "description_manual", "label": "📝 توضیحات", "format": "{value}", "enabled": false}]	\n	t	t	1	t	\N	\N	["#کامپیوتر", "#لپتاپ", "#خرید_لپتاپ"]	[{"field": "brand", "prefix": "#"}]	text_with_image	2026-08-30 20:28:30.794584	2026-08-30 20:28:30.794595
\.


--
-- Data for Name: posted_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.posted_messages (id, product_id, channel_id, platform, telegram_message_id, telegram_message_ids, last_caption, last_price, last_stock_qty, status, created_at, updated_at) FROM stdin;
146	123	9	TELEGRAM	175	[]	🖥 Microsoft Surface Pro 5\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\nSurface Pro 5، یک تبلت/لپتاپ ۲-در-۱ قدرتمند با پردازنده نسل هفتم اینتل و حافظه SSD سریع. این دستگاه با امکان اتصال LTE و همراه داشتن کیبورد بلوتوثی، یک ابزار ایده‌آل برای کارهای سیار و بهره‌وری در هر مکانی است.\n\n🔹 پردازنده Intel Core i5-7200U نسل هفتم\n🔹 ۸ گیگابایت حافظه رم DDR4\n🔹 ۲۵۶ گیگابایت حافظه SSD سریع\n🔹 صفحه نمایش لمسی ۲K با کیفیت بالا (12.5 اینچ)\n🔹 اتصال LTE برای اینترنت پرسرعت در هر مکان\n🔹 وزن سبک و قابل حمل (۰.۷۷ کیلوگرم)\n🔹 سیستم عامل ویندوز 10 Pro\n🔹 گرافیک مجتمع Intel HD Graphics 620\n🔹 پورت USB 3.0 برای انتقال سریع داده\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 58,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	58000000	1	ACTIVE	2026-09-03 00:11:40.811482	2026-09-03 11:32:29.966925
94	108	7	TELEGRAM	168544508	[]	🖥 Hp ProBook 650 G1\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 32,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	32400000	1	ACTIVE	2026-08-30 22:37:39.854907	2026-09-03 09:34:13.986122
142	120	9	TELEGRAM	171	[]	🖥 Hp ProBook 4530S\n\n⚡️ پردازنده: i3-2310M\n🧠 رم: 8GB\n💾 حافظه: 120 SSD + 320HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 27,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	27100000	1	ACTIVE	2026-09-02 00:28:07.58461	2026-09-03 09:32:48.393094
110	112	7	TELEGRAM	168548585	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i5-1035G7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 73,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	73200000	1	ACTIVE	2026-08-30 22:57:39.73668	2026-09-03 09:34:30.561132
135	119	6	TELEGRAM	31	[]	🖥 Samsung 2233SN\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 21.5" LCD FHD / 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 9,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	9800000	1	ACTIVE	2026-08-30 23:37:24.07036	2026-09-03 09:34:49.497205
140	86	9	TELEGRAM	169	[]	🖥 Lenovo ThinkPad T540P\n\n⚡ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: 1GB Nvidia GT730M\n📐 صفحه: 15.6 FHD Matte\n\n⭐️ Grade\n\n📝 ThinkPad T540P یک لپتاپ صنعتی قدرتمند برای انجام کارهای سنگین و برنامه‌نویسی است. با پردازنده قوی و کارت گرافیک مجزا، برای مهندسان و طراحان مناسب است. صفحه نمایش مات FHD، تجربه کاربری راحت‌تری ارائه می‌دهد.\n\n✅ مزایا:\n• پردازنده Intel Core i5 نسل چهارم\n• حافظه SSD 256 گیگابایتی\n• کارت گرافیک Nvidia GT730M\n• 8 گیگابایت رم DDR3\n• صفحه نمایش مات 15.6 اینچی\n\n⚠️ ملاحضات:\n• عمر باتری محدود\n• کارت گرافیک نسبتاً قدیمی\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #لپتاپ_لنوو #لپتاپ_زیر_۵۰_میلیون\n\n─────────────────\n💰 قیمت: 32,900,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡️ یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/09	32900000	1	ACTIVE	2026-08-31 19:17:44.270156	2026-08-31 19:17:44.270156
141	87	9	TELEGRAM	170	[]	🖥 Hp Zbook Fury G8\n\n⚡ پردازنده: i7-11850H\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 16GB Nvidia Quadro RTX 5000\n📐 صفحه: 17.3 FHD IPS\n\n⭐️ Grade\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #لپتاپ_اچ_پی #لپتاپ_بالای_۸۰_میلیون\n\n─────────────────\n💰 قیمت: 244,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡️ یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/07	244100000	1	ACTIVE	2026-08-31 19:52:44.387974	2026-08-31 19:52:44.387974
51	63	9	TELEGRAM	146	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i3 1115G4\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: INTEL UHD\n📐 صفحه: FHD IPS Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i3\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 21:47:05.172956	2026-09-03 11:32:29.620582
139	85	9	TELEGRAM	168	[]	🖥 Microsoft Surface Pro 5 LTE\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 44,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	44600000	1	ACTIVE	2026-08-31 18:42:44.34703	2026-09-03 09:32:30.852588
130	117	8	TELEGRAM	635	[]	🖥 Lenovo ThinkPad T540P\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: 1GB Nvidia GT730M\n📐 صفحه: 15.6 FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 36,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	36000000	1	ACTIVE	2026-08-30 23:27:23.533257	2026-09-03 09:33:34.645967
134	118	8	TELEGRAM	636	[]	🖥 Samsung 1900T\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 19" LCD QHD 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 8,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	8600000	1	ACTIVE	2026-08-30 23:32:23.067537	2026-09-03 09:33:38.074628
147	124	9	TELEGRAM	176	[]	🖥 Lenovo ThinkPad T540P\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: 1GB Nvidia GT730M\n📐 صفحه: 15.6 FHD Matte\n\n⭐️ -\n\nThinkPad T540P یک لپتاپ قدرتمند و بادوام برای متخصصان و کاربران حرفه‌ای است که به دنبال عملکرد بالا در یک بدنه مقاوم می‌باشند. این مدل با پردازنده Intel Core i5 و گرافیک Nvidia، برای کارهای محاسباتی سنگین و برنامه‌های کاربردی مختلف مناسب است. صفحه نمایش مات Full HD آن، تجربه بصری راحت و بدون بازتاب را فراهم می‌کند.\n\n🔹 پردازنده Intel Core i5-4300M\n🔹 حافظه رم 8GB DDR3\n🔹 حافظه SSD با ظرفیت 256GB\n🔹 کارت گرافیک Nvidia GT730M با 1GB حافظه\n🔹 صفحه نمایش 15.6 اینچی Full HD Matte\n🔹 درایو نوری DVD-RW\n🔹 پورت DisplayPort برای اتصال مانیتور خارجی\n🔹 چهار پورت USB برای اتصال دستگاه‌های جانبی\n🔹 حسگر اثر انگشت برای امنیت بیشتر\n🔹 پشتیبانی از قلم نوری (Pen Support)\n🔹 وزن نسبتاً سبک 2.41 کیلوگرم\n🔹 کیبورد با نور پس زمینه ندارد\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 36,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	36000000	1	ACTIVE	2026-09-03 06:07:52.100637	2026-09-03 11:32:30.394327
144	122	9	TELEGRAM	173	[]	🖥 Hp ProBook 650 G1\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\nلپتاپ ProBook 650 G1 یک گزینه مناسب برای کاربران حرفه‌ای و دانشجویان است که به دنبال یک دستگاه قابل اعتماد و با کارایی برای انجام وظایف روزمره و محاسبات متوسط هستند. این لپتاپ با پردازنده Intel Core i5 و هارد درایو 500 گیگابایتی، عملکرد قابل قبولی را ارائه می‌دهد.\n\n🔹 پردازنده Intel Core i5-4300M برای کارهای روزمره\n🔹 حافظه رم 8 گیگابایت برای اجرای همزمان برنامه‌ها\n🔹 هارد درایو 500 گیگابایتی برای ذخیره‌سازی حجم زیادی از داده\n🔹 صفحه نمایش 15.6 اینچی HD برای دیدن راحت محتوا\n🔹 پورت DisplayPort برای اتصال به مانیتورهای خارجی\n🔹 پورت LAN برای اتصال به شبکه‌های سیمی\n🔹 درایو DVD-RW برای خواندن و نوشتن دیسک‌های نوری\n🔹 پنج پورت USB برای اتصال انواع دستگاه‌های جانبی\n🔹 وزن 2.32 کیلوگرم، نسبتاً قابل حمل\n🔹 عمر باتری تا 5 ساعت در استفاده معمولی\n🔹 طراحی مقاوم و بادوام\n🔹 مناسب برای استفاده‌های اداری و تحصیلی\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 32,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	32400000	1	ACTIVE	2026-09-02 11:32:00.509242	2026-09-03 09:32:48.988815
133	118	7	TELEGRAM	168552830	[]	🖥 Samsung 1900T\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 19" LCD QHD 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 8,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	8600000	1	ACTIVE	2026-08-30 23:32:23.054566	2026-09-03 09:33:37.218863
136	119	7	TELEGRAM	168553494	[]	🖥 Samsung 2233SN\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 21.5" LCD FHD / 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 9,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	9800000	1	ACTIVE	2026-08-30 23:37:24.107548	2026-09-03 09:34:51.97653
137	119	8	TELEGRAM	637	[]	🖥 Samsung 2233SN\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 21.5" LCD FHD / 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 9,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	9800000	1	ACTIVE	2026-08-30 23:37:24.119258	2026-09-03 09:34:52.994904
69	102	6	TELEGRAM	14	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i5-1135 G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 14" FHD Touch Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	3	ACTIVE	2026-08-30 22:07:40.571315	2026-09-03 09:33:45.927869
59	67	9	TELEGRAM	148	[]	🖥 Dell Latitude e6520\n\n⚡️ پردازنده: i5-2220m\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 23,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	23200000	3	ACTIVE	2026-08-30 21:53:22.197406	2026-09-03 11:32:30.944521
92	74	9	TELEGRAM	157	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i5-1135 G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 14" FHD Touch Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	59800000	3	ACTIVE	2026-08-30 22:37:28.065501	2026-09-03 09:32:30.016491
143	121	9	TELEGRAM	172	[]	🖥 Hp Zbook Fury G8\n\n⚡️ پردازنده: i7-11850H\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 16GB Nvidia Quadro RTX 5000\n📐 صفحه: 17.3 FHD IPS\n\n⭐️ -\n\nZbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای کارهای سنگین و محاسبات پیچیده ایده‌آل است. صفحه نمایش بزرگ و باکیفیت، تجربه بصری بی‌نظیری را ارائه می‌دهد.\n\n🔹 پردازنده Intel Core i7-11850H نسل یازدهم\n🔹 ۱۶ گیگابایت رم DDR4 برای اجرای همزمان برنامه‌ها\n🔹 حافظه SSD با ظرفیت ۵۱۲ گیگابایت با سرعت بالا\n🔹 کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶ گیگابایت حافظه\n🔹 صفحه نمایش ۱۷.۳ اینچی FHD IPS با کیفیت تصویر عالی\n🔹 پورت‌های Thunderbolt برای اتصال دستگاه‌های سریع\n🔹 دارای پورت LAN برای اتصال با سیم\n🔹 وب‌کم با قابلیت تشخیص چهره (Facial Recognition)\n🔹 کیبورد با نور پس زمینه (Backlit Keyboard)\n🔹 حسگر اثر انگشت (Fingerprint) برای امنیت بیشتر\n🔹 دارای پورت‌های USB متعدد\n🔹 عمر باتری تا ۷ ساعت\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 267,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	267800000	1	ACTIVE	2026-09-02 11:27:20.786034	2026-09-03 09:32:48.711782
56	99	6	TELEGRAM	11	[]	🖥 Dell inspiron 3590\n\n⚡️ پردازنده: i3-7100u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 39,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	39100000	1	ACTIVE	2026-08-30 21:50:17.98133	2026-09-03 09:33:10.596109
49	94	7	TELEGRAM	168539009	[]	🖥 HP EliteDesk 800 G1 )مینی کیس(\n\n⚡️ پردازنده: i5-4590\n🧠 رم: 4GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: -\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پانزده_تا_بیست_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 17,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	17100000	2	ACTIVE	2026-08-30 21:45:16.774371	2026-09-03 09:33:44.404014
72	69	9	TELEGRAM	152	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB Nvidia Quadro K3100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 47,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	47600000	1	ACTIVE	2026-08-30 22:12:28.096688	2026-09-03 11:32:37.294249
131	83	9	TELEGRAM	166	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i7-1065g7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 83,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	83600000	1	ACTIVE	2026-08-30 23:27:23.964111	2026-09-03 09:32:30.398508
76	70	9	TELEGRAM	153	[]	🖥 Dell Precision 3530\n\n⚡️ پردازنده: i7-8750h\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 4GB P600 Nvidia Quadro\n📐 صفحه: 15.6 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 94,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	94000000	1	ACTIVE	2026-08-30 22:17:28.094486	2026-09-03 09:32:31.180005
60	65	9	TELEGRAM	149	[]	🖥 Apple MacBook Air 2017\n\n⚡️ پردازنده: i5\n🧠 رم: 8GB\n💾 حافظه: 128GB SSD\n🎮 گرافیک: intel\n📐 صفحه: FHD\n\n⭐️ -\n\nلپتاپ MacBook Air 2017 یک لپتاپ سبک و قابل حمل برای دانشجویان، کارمندان و کاربرانی است که به دنبال یک دستگاه با عملکرد مناسب برای کارهای روزمره و بهره‌وری هستند. این مدل با پردازنده Intel i5 و حافظه SSD، تجربه‌ای سریع و روان را ارائه می‌دهد.\n\n🔹 پردازنده Intel Core i5 نسل هفتم\n🔹 ۸ گیگابایت حافظه رم DDR3\n🔹 حافظه داخلی ۱۲۸ گیگابایت SSD\n🔹 صفحه نمایش ۱۴ اینچی با رزولوشن FHD\n🔹 گرافیک مجتمع Intel HD Graphics 6000\n🔹 طراحی باریک و سبک با وزن کم\n🔹 سیستم عامل macOS\n🔹 عمر باتری مناسب برای استفاده روزانه\n🔹 پورت‌های Thunderbolt 3 برای اتصال سریع\n🔹 بلندگوهای استریو با کیفیت\n🔹 کیبورد با نور پس‌زمینه\n🔹 حسگر اثر انگشت Touch ID\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Apple #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 21:57:28.408637	2026-09-03 09:32:37.653622
128	117	6	TELEGRAM	29	[]	🖥 Lenovo ThinkPad T540P\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: 1GB Nvidia GT730M\n📐 صفحه: 15.6 FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 36,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	36000000	1	ACTIVE	2026-08-30 23:27:23.475211	2026-09-03 09:33:30.301555
73	103	6	TELEGRAM	15	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB AMD Fire Pro 6100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 46,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	46400000	1	ACTIVE	2026-08-30 22:12:40.059138	2026-09-03 09:33:49.568599
77	104	6	TELEGRAM	16	[]	🖥 Hp Probook 650 G8\n\n⚡️ پردازنده: i5-1145G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 FHD\n\n⭐️ A++\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 81,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	81200000	2	ACTIVE	2026-08-30 22:17:40.47184	2026-09-03 09:33:54.77417
145	76	9	TELEGRAM	174	[]	🖥 Hp Probook 650 G8\n\n⚡️ پردازنده: i5-1145G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 FHD\n\n⭐️ A++\n\nProbook 650 G8 یک لپتاپ تجاری قدرتمند است که برای متخصصان و کاربران حرفه‌ای طراحی شده است. این لپتاپ با پردازنده نسل یازدهم اینتل و حافظه SSD سریع، عملکردی عالی برای کارهای روزمره و سنگین ارائه می‌دهد. ویژگی برجسته آن، وجود پورت Thunderbolt 4 است.\n\n🔹 پردازنده Intel Core i5-1145G7 نسل یازدهم\n🔹 حافظه رم ۸ گیگابایت DDR4\n🔹 حافظه داخلی ۲۵۶ گیگابایت SSD\n🔹 صفحه نمایش ۱۵.۶ اینچی با رزولوشن FHD (1920x1080)\n🔹 کارت گرافیک Intel Iris Xe Graphics\n🔹 پورت Thunderbolt 4 برای اتصال دستگاه‌های سریع\n🔹 دارای پورت HDMI برای اتصال به نمایشگر خارجی\n🔹 شبکه LAN با سرعت بالا برای اتصال سیمی\n🔹 حسگر اثر انگشت برای امنیت بیشتر\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 81,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	81200000	2	ACTIVE	2026-09-03 00:05:20.873639	2026-09-03 11:32:37.814305
64	66	9	TELEGRAM	150	[]	🖥 HP EliteDesk 800 G1 )مینی کیس(\n\n⚡️ پردازنده: i5-4590\n🧠 رم: 4GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: -\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پانزده_تا_بیست_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 17,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	17100000	2	ACTIVE	2026-08-30 22:02:28.154717	2026-09-03 09:32:37.865151
88	73	9	TELEGRAM	156	[]	🖥 Lenovo V130\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 12GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:32:28.121783	2026-09-03 09:32:42.605928
53	95	7	TELEGRAM	168539255	[]	🖥 Dell Latitude e6520\n\n⚡️ پردازنده: i5-2220m\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 23,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	23200000	3	ACTIVE	2026-08-30 21:47:07.135486	2026-09-03 09:32:57.029679
36	97	6	TELEGRAM	5	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB Nvidia Quadro K3100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 47,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	47600000	1	ACTIVE	2026-08-30 20:54:12.01456	2026-09-03 09:33:01.713131
41	98	7	TELEGRAM	168533930	[]	🖥 Dell Precision 3530\n\n⚡️ پردازنده: i7-8750h\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 4GB P600 Nvidia Quadro\n📐 صفحه: 15.6 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 94,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	94000000	1	ACTIVE	2026-08-30 20:56:17.268665	2026-09-03 09:33:08.683513
90	107	7	TELEGRAM	168544040	[]	🖥 Hp Zbook Fury G8\n\n⚡️ پردازنده: i7-11850H\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 16GB Nvidia Quadro RTX 5000\n📐 صفحه: 17.3 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 267,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	267800000	1	ACTIVE	2026-08-30 22:32:39.708395	2026-09-03 09:34:10.173054
37	97	8	TELEGRAM	594	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB Nvidia Quadro K3100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 47,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	47600000	1	ACTIVE	2026-08-30 20:54:12.841274	2026-09-03 09:33:05.386713
39	98	8	TELEGRAM	600	[]	🖥 Dell Precision 3530\n\n⚡️ پردازنده: i7-8750h\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 4GB P600 Nvidia Quadro\n📐 صفحه: 15.6 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 94,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	94000000	1	ACTIVE	2026-08-30 20:56:16.551856	2026-09-03 09:33:10.378584
58	99	8	TELEGRAM	612	[]	🖥 Dell inspiron 3590\n\n⚡️ پردازنده: i3-7100u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 39,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	39100000	1	ACTIVE	2026-08-30 21:50:18.080421	2026-09-03 09:33:13.996647
63	100	8	TELEGRAM	613	[]	🖥 HP ProBook 450 G6\n\n⚡️ پردازنده: i5-8250u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 52,500,000 تومان\n📦 ❌ ناموجود\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	52500000	0	ACTIVE	2026-08-30 21:57:40.52214	2026-09-03 09:33:17.591373
71	102	8	TELEGRAM	615	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i5-1135 G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 14" FHD Touch Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	3	ACTIVE	2026-08-30 22:07:40.603711	2026-09-03 09:33:49.372836
75	103	8	TELEGRAM	617	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB AMD Fire Pro 6100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 46,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	46400000	1	ACTIVE	2026-08-30 22:12:40.091958	2026-09-03 09:33:54.500513
79	104	8	TELEGRAM	619	[]	🖥 Hp Probook 650 G8\n\n⚡️ پردازنده: i5-1145G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 FHD\n\n⭐️ A++\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 81,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	81200000	2	ACTIVE	2026-08-30 22:17:40.537486	2026-09-03 09:33:58.868807
57	99	7	TELEGRAM	168539728	[]	🖥 Dell inspiron 3590\n\n⚡️ پردازنده: i3-7100u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 39,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	39100000	1	ACTIVE	2026-08-30 21:50:18.053147	2026-09-03 09:33:12.964227
62	100	7	TELEGRAM	168540997	[]	🖥 HP ProBook 450 G6\n\n⚡️ پردازنده: i5-8250u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 52,500,000 تومان\n📦 ❌ ناموجود\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	52500000	0	ACTIVE	2026-08-30 21:57:40.505963	2026-09-03 09:33:16.601522
70	102	7	TELEGRAM	168541697	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i5-1135 G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 14" FHD Touch Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	3	ACTIVE	2026-08-30 22:07:40.590992	2026-09-03 09:33:48.525787
91	107	8	TELEGRAM	624	[]	🖥 Hp Zbook Fury G8\n\n⚡️ پردازنده: i7-11850H\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 16GB Nvidia Quadro RTX 5000\n📐 صفحه: 17.3 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 267,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	267800000	1	ACTIVE	2026-08-30 22:32:39.724198	2026-09-03 09:34:11.330464
52	95	6	TELEGRAM	10	[]	🖥 Dell Latitude e6520\n\n⚡️ پردازنده: i5-2220m\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 23,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	23200000	3	ACTIVE	2026-08-30 21:47:07.116334	2026-09-03 09:32:54.191965
34	96	6	TELEGRAM	4	[]	🖥 Dell inspiron 7567 Gaming\n\n⚡️ پردازنده: i7-7700HQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia GTX 1050TI 4GB DDr5\n📐 صفحه: 15.6 UHD 4K IPS Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #گیمینگ #LTE #i7\n\n─────────────────\n💰 قیمت: 95,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	95200000	1	ACTIVE	2026-08-30 20:52:10.586355	2026-09-03 09:32:59.146261
93	108	6	TELEGRAM	20	[]	🖥 Hp ProBook 650 G1\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 32,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	32400000	1	ACTIVE	2026-08-30 22:37:39.840486	2026-09-03 09:34:11.526901
74	103	7	TELEGRAM	168542182	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB AMD Fire Pro 6100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 46,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	46400000	1	ACTIVE	2026-08-30 22:12:40.078378	2026-09-03 09:33:52.9625
78	104	7	TELEGRAM	168542599	[]	🖥 Hp Probook 650 G8\n\n⚡️ پردازنده: i5-1145G7\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 FHD\n\n⭐️ A++\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 81,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	81200000	2	ACTIVE	2026-08-30 22:17:40.516287	2026-09-03 09:33:57.157908
89	107	6	TELEGRAM	19	[]	🖥 Hp Zbook Fury G8\n\n⚡️ پردازنده: i7-11850H\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 16GB Nvidia Quadro RTX 5000\n📐 صفحه: 17.3 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 267,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	267800000	1	ACTIVE	2026-08-30 22:32:39.691442	2026-09-03 09:34:07.856657
129	117	7	TELEGRAM	168552609	[]	🖥 Lenovo ThinkPad T540P\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: 1GB Nvidia GT730M\n📐 صفحه: 15.6 FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 36,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	36000000	1	ACTIVE	2026-08-30 23:27:23.518106	2026-09-03 09:33:32.694874
132	118	6	TELEGRAM	30	[]	🖥 Samsung 1900T\n\n⚡️ پردازنده: -\n🧠 رم: -\n💾 حافظه: -\n🎮 گرافیک: -\n📐 صفحه: 19" LCD QHD 60HZ\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Samsung #پنج_تا_ده_میلیون #گرافیک_دار\n\n─────────────────\n💰 قیمت: 8,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	8600000	1	ACTIVE	2026-08-30 23:32:22.9929	2026-09-03 09:33:34.868173
97	109	6	TELEGRAM	21	[]	🖥 HP Zbook 17 G3\n\n⚡️ پردازنده: i7-6820HQ\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia QUADRO M1000m\n📐 صفحه: 17,3 inch fhd ips\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 71,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	71400000	1	ACTIVE	2026-08-30 22:42:40.095964	2026-09-03 09:34:16.131899
111	112	8	TELEGRAM	630	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i5-1035G7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 73,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	73200000	1	ACTIVE	2026-08-30 22:57:39.751058	2026-09-03 09:34:34.567464
95	108	8	TELEGRAM	625	[]	🖥 Hp ProBook 650 G1\n\n⚡️ پردازنده: i5-4300M\n🧠 رم: 8GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 32,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	32400000	1	ACTIVE	2026-08-30 22:37:39.865416	2026-09-03 09:34:15.930346
99	109	8	TELEGRAM	627	[]	🖥 HP Zbook 17 G3\n\n⚡️ پردازنده: i7-6820HQ\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia QUADRO M1000m\n📐 صفحه: 17,3 inch fhd ips\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 71,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	71400000	1	ACTIVE	2026-08-30 22:42:40.120746	2026-09-03 09:34:19.783465
101	110	6	TELEGRAM	22	[]	🖥 Microsoft Surface Go 3 -1926\n\n⚡️ پردازنده: i3-10100y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #شصت_تا_هفتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 65,300,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	65300000	1	ACTIVE	2026-08-30 22:47:40.272018	2026-09-03 09:34:20.17355
103	110	8	TELEGRAM	628	[]	🖥 Microsoft Surface Go 3 -1926\n\n⚡️ پردازنده: i3-10100y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #شصت_تا_هفتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 65,300,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	65300000	1	ACTIVE	2026-08-30 22:47:40.295995	2026-09-03 09:34:23.404437
105	111	6	TELEGRAM	23	[]	🖥 Microsoft Surface Go 2 - 1824\n\n⚡️ پردازنده: Pentium 4415y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 30,500,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	30500000	2	ACTIVE	2026-08-30 22:52:40.002772	2026-09-03 09:34:23.62384
113	113	6	TELEGRAM	25	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i7-1065g7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 83,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	83600000	1	ACTIVE	2026-08-30 23:02:40.164278	2026-09-03 09:34:35.014163
66	101	7	TELEGRAM	168541148	[]	🖥 Lenovo V130\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 12GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:02:40.271195	2026-09-03 09:33:20.150637
122	115	7	TELEGRAM	168550621	[]	🖥 Microsoft Surface Pro 5 LTE\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 44,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44600000	1	ACTIVE	2026-08-30 23:12:50.660336	2026-09-03 09:33:27.783392
98	109	7	TELEGRAM	168544921	[]	🖥 HP Zbook 17 G3\n\n⚡️ پردازنده: i7-6820HQ\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia QUADRO M1000m\n📐 صفحه: 17,3 inch fhd ips\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 71,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	71400000	1	ACTIVE	2026-08-30 22:42:40.109622	2026-09-03 09:34:18.483526
102	110	7	TELEGRAM	168545779	[]	🖥 Microsoft Surface Go 3 -1926\n\n⚡️ پردازنده: i3-10100y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #شصت_تا_هفتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 65,300,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	65300000	1	ACTIVE	2026-08-30 22:47:40.284947	2026-09-03 09:34:22.564532
106	111	7	TELEGRAM	168547091	[]	🖥 Microsoft Surface Go 2 - 1824\n\n⚡️ پردازنده: Pentium 4415y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 30,500,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	30500000	2	ACTIVE	2026-08-30 22:52:40.040067	2026-09-03 09:34:26.176397
114	113	7	TELEGRAM	168549474	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i7-1065g7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 83,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	83600000	1	ACTIVE	2026-08-30 23:02:40.179767	2026-09-03 09:34:37.355633
104	77	9	TELEGRAM	160	[]	🖥 Sony Vaio VJPJ11C11N\n\n⚡️ پردازنده: i7-8565u\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3 FHD Ips 8BIT\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Sony_Vaio #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #Pen #LTE #VAIO\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	59800000	1	ACTIVE	2026-08-30 22:52:28.061216	2026-09-03 09:32:43.368555
116	80	9	TELEGRAM	163	[]	🖥 Microsoft Surface Go 3 -1926\n\n⚡️ پردازنده: i3-10100y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #شصت_تا_هفتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 65,300,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	65300000	1	ACTIVE	2026-08-30 23:07:28.069323	2026-09-03 09:32:48.107921
67	101	8	TELEGRAM	614	[]	🖥 Lenovo V130\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 12GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:02:40.286175	2026-09-03 09:33:21.023901
107	111	8	TELEGRAM	629	[]	🖥 Microsoft Surface Go 2 - 1824\n\n⚡️ پردازنده: Pentium 4415y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 30,500,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	30500000	2	ACTIVE	2026-08-30 22:52:40.065991	2026-09-03 09:34:27.996702
115	113	8	TELEGRAM	631	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i7-1065g7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 83,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	83600000	1	ACTIVE	2026-08-30 23:02:40.191923	2026-09-03 09:34:39.230445
118	114	7	TELEGRAM	168550329	[]	🖥 Microsoft Surface Book 2\n\n⚡️ پردازنده: i7-8650u\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia GTX 1050\n📐 صفحه: 13.3" 4K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 103,700,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	103700000	1	ACTIVE	2026-08-30 23:07:39.312411	2026-09-03 09:34:41.765745
119	114	8	TELEGRAM	632	[]	🖥 Microsoft Surface Book 2\n\n⚡️ پردازنده: i7-8650u\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia GTX 1050\n📐 صفحه: 13.3" 4K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 103,700,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	103700000	1	ACTIVE	2026-08-30 23:07:39.320689	2026-09-03 09:34:42.802681
127	82	9	TELEGRAM	165	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i5-1035G7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 73,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	73200000	1	ACTIVE	2026-08-30 23:17:39.780561	2026-09-03 09:32:43.016835
32	90	6	TELEGRAM	2	[]	🖥 Hp ProBook 4530S\n\n⚡️ پردازنده: i3-2310M\n🧠 رم: 8GB\n💾 حافظه: 120 SSD + 320HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 27,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	27100000	1	ACTIVE	2026-08-30 20:26:24.910284	2026-09-03 09:33:21.235975
121	115	6	TELEGRAM	27	[]	🖥 Microsoft Surface Pro 5 LTE\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 44,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44600000	1	ACTIVE	2026-08-30 23:12:50.646199	2026-09-03 09:33:25.472043
81	105	6	TELEGRAM	17	[]	🖥 Sony Vaio VJPJ11C11N\n\n⚡️ پردازنده: i7-8565u\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3 FHD Ips 8BIT\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Sony_Vaio #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #Pen #LTE #VAIO\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	1	ACTIVE	2026-08-30 22:22:39.981202	2026-09-03 09:33:59.107564
82	105	7	TELEGRAM	168543155	[]	🖥 Sony Vaio VJPJ11C11N\n\n⚡️ پردازنده: i7-8565u\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3 FHD Ips 8BIT\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Sony_Vaio #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #Pen #LTE #VAIO\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	1	ACTIVE	2026-08-30 22:22:39.995811	2026-09-03 09:34:02.170994
85	106	6	TELEGRAM	18	[]	🖥 Hp Zbook G2\n\n⚡️ پردازنده: i7-4710 MQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia Quadro K1100 2GB DDr5\n📐 صفحه: 15.6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:27:39.774153	2026-09-03 09:34:03.349135
117	114	6	TELEGRAM	26	[]	🖥 Microsoft Surface Book 2\n\n⚡️ پردازنده: i7-8650u\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia GTX 1050\n📐 صفحه: 13.3" 4K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 103,700,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	103700000	1	ACTIVE	2026-08-30 23:07:39.299379	2026-09-03 09:34:39.430783
40	98	6	TELEGRAM	6	[]	🖥 Dell Precision 3530\n\n⚡️ پردازنده: i7-8750h\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 4GB P600 Nvidia Quadro\n📐 صفحه: 15.6 FHD IPS\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 94,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	94000000	1	ACTIVE	2026-08-30 20:56:16.857603	2026-09-03 09:33:05.583571
61	100	6	TELEGRAM	12	[]	🖥 HP ProBook 450 G6\n\n⚡️ پردازنده: i5-8250u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 52,500,000 تومان\n📦 ❌ ناموجود\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	52500000	0	ACTIVE	2026-08-30 21:57:40.466493	2026-09-03 09:33:14.217385
65	101	6	TELEGRAM	13	[]	🖥 Lenovo V130\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 12GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Lenovo #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:02:40.253763	2026-09-03 09:33:17.809788
123	115	8	TELEGRAM	633	[]	🖥 Microsoft Surface Pro 5 LTE\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 44,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44600000	1	ACTIVE	2026-08-30 23:12:50.672154	2026-09-03 09:33:30.067602
83	105	8	TELEGRAM	620	[]	🖥 Sony Vaio VJPJ11C11N\n\n⚡️ پردازنده: i7-8565u\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 13.3 FHD Ips 8BIT\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Sony_Vaio #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #Pen #LTE #VAIO\n\n─────────────────\n💰 قیمت: 59,800,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	59800000	1	ACTIVE	2026-08-30 22:22:40.007927	2026-09-03 09:34:03.129758
54	95	8	TELEGRAM	610	[]	🖥 Dell Latitude e6520\n\n⚡️ پردازنده: i5-2220m\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15.6 HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بیست_تا_سی_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 23,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	23200000	3	ACTIVE	2026-08-30 21:47:07.153574	2026-09-03 09:32:58.922421
35	96	7	TELEGRAM	168533602	[]	🖥 Dell inspiron 7567 Gaming\n\n⚡️ پردازنده: i7-7700HQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia GTX 1050TI 4GB DDr5\n📐 صفحه: 15.6 UHD 4K IPS Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #گیمینگ #LTE #i7\n\n─────────────────\n💰 قیمت: 95,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	95200000	1	ACTIVE	2026-08-30 20:52:11.699928	2026-09-03 09:33:01.494682
38	97	7	TELEGRAM	168533738	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB Nvidia Quadro K3100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 47,600,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	47600000	1	ACTIVE	2026-08-30 20:54:13.220901	2026-09-03 09:33:04.502861
86	106	7	TELEGRAM	168543615	[]	🖥 Hp Zbook G2\n\n⚡️ پردازنده: i7-4710 MQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia Quadro K1100 2GB DDr5\n📐 صفحه: 15.6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:27:39.793573	2026-09-03 09:34:05.688047
68	68	9	TELEGRAM	151	[]	🖥 Dell inspiron 7567 Gaming\n\n⚡️ پردازنده: i7-7700HQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia GTX 1050TI 4GB DDr5\n📐 صفحه: 15.6 UHD 4K IPS Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #بالای_هشتاد_میلیون #گرافیک_دار #گیمینگ #LTE #i7\n\n─────────────────\n💰 قیمت: 95,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	95200000	1	ACTIVE	2026-08-30 22:07:28.09623	2026-09-03 13:32:29.588931
87	106	8	TELEGRAM	622	[]	🖥 Hp Zbook G2\n\n⚡️ پردازنده: i7-4710 MQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia Quadro K1100 2GB DDr5\n📐 صفحه: 15.6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:27:39.806812	2026-09-03 09:34:07.604185
33	91	6	TELEGRAM	3	[]	🖥 Toshiba Tecra A40-J\n\n⚡️ پردازنده: i3 1115G4\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: INTEL UHD\n📐 صفحه: FHD IPS Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Toshiba #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i3\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 20:29:01.680812	2026-09-03 09:33:21.449129
45	93	6	TELEGRAM	8	[]	🖥 Apple MacBook Air 2017\n\n⚡️ پردازنده: i5\n🧠 رم: 8GB\n💾 حافظه: 128GB SSD\n🎮 گرافیک: intel\n📐 صفحه: FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Apple #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 21:40:17.105681	2026-09-03 09:33:21.676647
42	92	6	TELEGRAM	7	[]	🖥 Asus 1215N Mini\n\n⚡️ پردازنده: Athom-D525\n🧠 رم: 6GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #ASUS #پانزده_تا_بیست_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 15,900,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	15900000	1	ACTIVE	2026-08-30 21:35:15.780839	2026-09-03 09:33:38.279812
55	64	9	TELEGRAM	177	[]	🖥 Asus 1215N Mini\n\n⚡️ پردازنده: Athom-D525\n🧠 رم: 6GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\nلپتاپ 1215N Mini ایسوس، یک گزینه سبک و قابل حمل برای کارهای روزمره و دانشجویی است. با وجود عدم باتری، این مدل برای استفاده در محیط‌های ثابت مانند دفتر کار یا خانه ایده‌آل است و امکان اتصال به برق را به صورت مداوم فراهم می‌کند. این لپتاپ با پردازنده اتم و هارددیسک 500 گیگابایتی، نیازهای اساسی شما را برآورده می‌کند.\n\n🔹 پردازنده Intel Atom D525 برای کاربری سبک\n🔹 رم 6 گیگابایت برای اجرای همزمان برنامه‌ها\n🔹 هارددیسک 500 گیگابایتی فضای ذخیره‌سازی کافی\n🔹 صفحه نمایش HD با کیفیت تصویر مناسب\n🔹 پورت LAN برای اتصال به شبکه سیمی\n🔹 خروجی HDMI برای اتصال به نمایشگر خارجی\n🔹 سه پورت USB برای اتصال لوازم جانبی\n🔹 وزن سبک 1.5 کیلوگرمی برای حمل آسان\n🔹 طراحی فشرده و جمع‌وجور\n🔹 مناسب برای کارهای متنی و وب‌گردی\n🔹 سیستم عامل ویندوز (پیش‌فرض)\n🔹 قابلیت ارتقاء رم (بررسی با سازنده)\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #ASUS #پانزده_تا_بیست_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 15,900,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	15900000	1	ACTIVE	2026-08-30 21:50:03.871733	2026-09-03 11:32:30.718026
46	93	7	TELEGRAM	168538251	[]	🖥 Apple MacBook Air 2017\n\n⚡️ پردازنده: i5\n🧠 رم: 8GB\n💾 حافظه: 128GB SSD\n🎮 گرافیک: intel\n📐 صفحه: FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Apple #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 21:40:17.153535	2026-09-03 09:33:24.097234
43	92	7	TELEGRAM	168537742	[]	🖥 Asus 1215N Mini\n\n⚡️ پردازنده: Athom-D525\n🧠 رم: 6GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #ASUS #پانزده_تا_بیست_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 15,900,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	15900000	1	ACTIVE	2026-08-30 21:35:15.813205	2026-09-03 09:33:40.644187
138	84	9	TELEGRAM	167	[]	🖥 Microsoft Surface Book 2\n\n⚡️ پردازنده: i7-8650u\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia GTX 1050\n📐 صفحه: 13.3" 4K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #بالای_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 103,700,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	103700000	1	ACTIVE	2026-08-31 11:04:31.383257	2026-09-03 09:32:30.627722
120	81	9	TELEGRAM	164	[]	🖥 Microsoft Surface Go 2 - 1824\n\n⚡️ پردازنده: Pentium 4415y\n🧠 رم: 8GB\n💾 حافظه: 120GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 10.5" FHD Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 30,500,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	30500000	2	ACTIVE	2026-08-30 23:12:38.159535	2026-09-03 09:32:38.113602
80	71	9	TELEGRAM	154	[]	🖥 Dell inspiron 3590\n\n⚡️ پردازنده: i3-7100u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #سی_تا_چهل_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 39,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	39100000	1	ACTIVE	2026-08-30 22:22:28.10505	2026-09-03 09:32:38.360523
96	75	9	TELEGRAM	158	[]	🖥 Dell Precision M6800\n\n⚡️ پردازنده: i7-4810MQ\n🧠 رم: 16GB\n💾 حافظه: 128GB SSD +320GB HDD\n🎮 گرافیک: 2GB AMD Fire Pro 6100\n📐 صفحه: 17.3" FHD Matte\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Dell #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 46,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	46400000	1	ACTIVE	2026-08-30 22:42:28.105888	2026-09-03 09:32:42.8066
108	78	9	TELEGRAM	161	[]	🖥 Hp Zbook G2\n\n⚡️ پردازنده: i7-4710 MQ\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: Nvidia Quadro K1100 2GB DDr5\n📐 صفحه: 15.6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #چهل_تا_پنجاه_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 44,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	44000000	1	ACTIVE	2026-08-30 22:57:28.162177	2026-09-03 09:32:43.579957
44	92	8	TELEGRAM	604	[]	🖥 Asus 1215N Mini\n\n⚡️ پردازنده: Athom-D525\n🧠 رم: 6GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: HD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #ASUS #پانزده_تا_بیست_میلیون #گرافیک_دار #Touch #Pen #LTE\n\n─────────────────\n💰 قیمت: 15,900,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	15900000	1	ACTIVE	2026-08-30 21:35:15.827276	2026-09-03 09:33:41.891595
84	72	9	TELEGRAM	155	[]	🖥 HP ProBook 450 G6\n\n⚡️ پردازنده: i5-8250u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 15,6 FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 52,500,000 تومان\n📦 ❌ ناموجود\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	52500000	0	ACTIVE	2026-08-30 22:27:28.146582	2026-09-03 11:32:37.509024
112	79	9	TELEGRAM	162	[]	🖥 HP Zbook 17 G3\n\n⚡️ پردازنده: i7-6820HQ\n🧠 رم: 16GB\n💾 حافظه: 512GB SSD\n🎮 گرافیک: 2GB Nvidia QUADRO M1000m\n📐 صفحه: 17,3 inch fhd ips\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #i7\n\n─────────────────\n💰 قیمت: 71,400,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @Nick_Bri\n🔄 1405/06/12	71400000	1	ACTIVE	2026-08-30 23:02:28.063675	2026-09-03 09:32:47.887969
47	93	8	TELEGRAM	607	[]	🖥 Apple MacBook Air 2017\n\n⚡️ پردازنده: i5\n🧠 رم: 8GB\n💾 حافظه: 128GB SSD\n🎮 گرافیک: intel\n📐 صفحه: FHD\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Apple #پنجاه_تا_شصت_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 50,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	50100000	1	ACTIVE	2026-08-30 21:40:17.168194	2026-09-03 09:33:25.256886
50	94	8	TELEGRAM	609	[]	🖥 HP EliteDesk 800 G1 )مینی کیس(\n\n⚡️ پردازنده: i5-4590\n🧠 رم: 4GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: -\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پانزده_تا_بیست_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 17,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	17100000	2	ACTIVE	2026-08-30 21:45:16.790645	2026-09-03 09:33:45.731557
48	94	6	TELEGRAM	9	[]	🖥 HP EliteDesk 800 G1 )مینی کیس(\n\n⚡️ پردازنده: i5-4590\n🧠 رم: 4GB\n💾 حافظه: 500GB HDD\n🎮 گرافیک: intel\n📐 صفحه: -\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #HP #پانزده_تا_بیست_میلیون #گرافیک_دار #LTE #لپتاپ_دانشجویی #لپتاپ_اداری #i5\n\n─────────────────\n💰 قیمت: 17,100,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	17100000	2	ACTIVE	2026-08-30 21:45:16.752235	2026-09-03 09:33:42.097967
109	112	6	TELEGRAM	24	[]	🖥 Microsoft Surface Laptop 3\n\n⚡️ پردازنده: i5-1035G7\n🧠 رم: 16GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #هفتاد_تا_هشتاد_میلیون #گرافیک_دار #Touch #Pen #LTE #لپتاپ_دانشجویی\n\n─────────────────\n💰 قیمت: 73,200,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	73200000	1	ACTIVE	2026-08-30 22:57:39.720602	2026-09-03 09:34:28.202285
124	116	6	TELEGRAM	28	[]	🖥 Microsoft Surface Pro 5\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 58,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	58000000	1	ACTIVE	2026-08-30 23:17:39.381064	2026-09-03 09:34:43.061718
125	116	7	TELEGRAM	168551314	[]	🖥 Microsoft Surface Pro 5\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 58,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	58000000	1	ACTIVE	2026-08-30 23:17:39.398926	2026-09-03 09:34:45.624638
126	116	8	TELEGRAM	634	[]	🖥 Microsoft Surface Pro 5\n\n⚡️ پردازنده: i5-7200u\n🧠 رم: 8GB\n💾 حافظه: 256GB SSD\n🎮 گرافیک: intel\n📐 صفحه: 12.5" 2K Touch\n\n⭐️ -\n\n🎯 مناسب برای\n#لپتاپ #کامپیوتر #Microsoft #پنجاه_تا_شصت_میلیون #گرافیک_دار #Touch #LTE #لپتاپ_دانشجویی #لپتاپ_اداری\n\n─────────────────\n💰 قیمت: 58,000,000 تومان\n📦 موجود ✅\n─────────────────\n\n🛡 یکماه گارانتی سخت افزاری مکتوب به همراه فاکتور معتبر\n\n➕ امکان گارانتی بیشتر:\n🔸 ۶ ماهه با ۷٪ افزایش قیمت\n🔸 ۱ ساله با ۱۰٪ افزایش قیمت\n\n📞 سفارش: @HeMyti\n🔄 1405/06/12	58000000	1	ACTIVE	2026-08-30 23:17:39.409512	2026-09-03 09:34:49.058668
\.


--
-- Data for Name: posting_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.posting_settings (id, customer_id, auto_publish_enabled, interval_hours, posting_start_hour, posting_end_hour, auto_ai_description, last_post_at, created_at, updated_at, interval_minutes) FROM stdin;
7	5	t	1	0	24	t	2026-08-30 23:37:24.141059	2026-08-30 20:27:40.683887	2026-08-30 23:37:24.142094	1
8	1	f	1	0	24	f	2026-08-31 19:52:44.432267	2026-08-30 20:46:36.35146	2026-08-31 20:08:22.612657	30
2	4	f	3	9	22	f	\N	2026-08-26 17:49:00.734891	2026-08-26 17:49:00.738766	\N
\.


--
-- Data for Name: product_platform_media; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.product_platform_media (id, product_id, platform, file_id, media_order, uploaded_by_customer, created_at, updated_at) FROM stdin;
20	76	TELEGRAM	AgACAgQAAxkBAAIJ7GqO0vTxuxztr3-FVV7XXBFnweHGAAKvDWsbdf5gUHt_e2X2U3ssAQADAgADeQADPQQ	0	t	2026-09-03 00:05:13.842143	2026-09-03 00:05:13.848811
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.products (id, customer_id, business_id, sub_category_key, sku, product_name, price, stock_qty, is_available, description_custom, image_url, specs, publish_status, created_at, updated_at, ai_description, ai_pros, ai_cons) FROM stdin;
74	1	9	laptop	13	Tecra A40-J	59800000	3	t	\N	\N	{"cpu": "i5-1135 G7", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Toshiba", "screen": "FHD Touch Matte", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 09:29:31.593723	2026-09-03 23:32:28.746926	\N	[]	[]
83	1	9	laptop	27	Surface Laptop 3	83600000	1	t	صفحه ترک دارد	\N	{"dp": "ندارد", "cpu": "i7-1065g7", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "2K Touch", "weight": "1.54", "storage": "256GB SSD", "usb_ports": 1, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 09:29:31.594065	2026-09-03 23:32:28.747055	\N	[]	[]
84	1	9	laptop	28	Surface Book 2	103700000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-8650u", "gpu": "2GB Nvidia GTX 1050", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "4K Touch", "weight": "1.64", "storage": "512GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 8, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 09:29:31.594102	2026-09-03 23:32:28.747125	\N	[]	[]
85	1	9	laptop	29	Surface Pro 5 LTE	44600000	1	t	صفحه ترک دارد	\N	{"cpu": "i5-7200u", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Microsoft", "screen": "2K Touch", "weight": "0.77", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 09:29:31.594146	2026-09-03 23:32:28.74716	\N	[]	[]
95	5	4	laptop	6	Latitude e6520	23200000	3	t	با باتری نو با گارانتی ۴ ماهه + ۲ تومان	\N	{"cpu": "i5-2220m", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "HD", "weight": "2.5", "storage": "120GB SSD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.531696	2026-09-03 23:32:29.833003	\N	[]	[]
96	5	4	laptop	7	inspiron 7567 Gaming	95200000	1	t	\N	\N	{"cpu": "i7-7700HQ", "gpu": "Nvidia GTX 1050TI 4GB DDr5", "lte": "ندارد", "ram": "16GB", "brand": "Dell", "screen": "UHD 4K IPS Matte", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 18:42:44.531821	2026-09-03 23:32:29.833025	\N	[]	[]
97	5	4	laptop	8	Precision M6800	47600000	1	t	\N	\N	{"cpu": "i7-4810MQ", "gpu": "2GB Nvidia Quadro K3100", "lte": "ندارد", "ram": "16GB", "x360": "ندارد", "brand": "Dell", "dvd_rw": "دارد", "screen": "FHD Matte", "storage": "128GB SSD +320GB HDD", "pen_support": "ندارد", "touch_screen": "ندارد", "backlit_keyboard": "دارد"}	PUBLISHED	2026-08-29 18:42:44.531942	2026-09-03 23:32:29.833037	\N	[]	[]
103	5	4	laptop	16	Precision M6800	46400000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-4810MQ", "gpu": "2GB AMD Fire Pro 6100", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "dvd_rw": "دارد", "screen": "FHD Matte", "weight": "3.58", "storage": "128GB SSD +320GB HDD", "usb_ports": 4, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.53267	2026-09-03 23:32:29.833106	\N	[]	[]
104	5	4	laptop	17	Probook 650 G8	81200000	2	t	\N	\N	{"dp": "ندارد", "cpu": "i5-1145G7", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "grade": "A++", "dvd_rw": "ندارد", "screen": "FHD", "weight": "1.74", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 6, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.532761	2026-09-03 23:32:29.833119	\N	[]	[]
70	1	9	laptop	9	Precision 3530	94000000	1	t	\N	\N	{"cpu": "i7-8750h", "gpu": "4GB P600 Nvidia Quadro", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "FHD IPS", "weight": "3.72", "storage": "512GB SSD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593549	2026-09-03 23:32:28.74689	\N	[]	[]
98	5	4	laptop	9	Precision 3530	94000000	1	t	\N	\N	{"cpu": "i7-8750h", "gpu": "4GB P600 Nvidia Quadro", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "FHD IPS", "weight": "3.72", "storage": "512GB SSD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.532065	2026-09-03 23:32:29.833061	\N	[]	[]
99	5	4	laptop	10	inspiron 3590	39100000	1	t	\N	\N	{"cpu": "i3-7100u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "FHD", "weight": "2.02", "storage": "256GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.532185	2026-09-03 23:32:29.833049	\N	[]	[]
100	5	4	laptop	11	ProBook 450 G6	52500000	0	f	\N	\N	{"cpu": "i5-8250u", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "HP", "screen": "FHD", "weight": "2", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 18:42:44.532314	2026-09-03 23:32:29.833072	\N	[]	[]
101	5	4	laptop	12	V130	44000000	1	t	\N	\N	{"cpu": "i5-7200u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "12GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Lenovo", "screen": "FHD", "weight": "1.8", "storage": "256GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.532439	2026-09-03 23:32:29.833083	\N	[]	[]
30	4	3	laptop	LP001	IdeaPad 5 Pro	42500000	5	t	لپتاپی قدرتمند برای کار و بازی	\N	{"cpu": "Core i7-12700H", "gpu": "RTX 3050 4GB", "ram": "16GB", "brand": "Lenovo", "screen": "16 اینچ 2.5K", "storage": "512GB SSD"}	PENDING	2026-08-26 17:48:45.374787	2026-08-26 17:48:45.374787	\N	[]	[]
31	4	3	laptop	LP002	ROG Strix G16	65000000	3	t	لپتاپ گیمینگ حرفه‌ای	\N	{"cpu": "Core i9-13900H", "gpu": "RTX 4060 8GB", "ram": "32GB", "brand": "ASUS", "screen": "16 اینچ FHD 165Hz", "storage": "1TB SSD"}	PENDING	2026-08-26 17:48:45.375223	2026-08-26 17:48:45.375223	\N	[]	[]
105	5	4	laptop	18	VJPJ11C11N	59800000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-8565u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Sony Vaio", "dvd_rw": "ندارد", "screen": "FHD Ips 8BIT", "weight": "1.64", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 6, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.532915	2026-09-03 23:32:29.833131	\N	[]	[]
106	5	4	laptop	19	Zbook G2	44000000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-4710 MQ", "gpu": "Nvidia Quadro K1100 2GB DDr5", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "ندارد", "screen": "FHD", "weight": "2.82", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.533043	2026-09-03 23:32:29.833142	\N	[]	[]
107	5	4	laptop	20	Zbook Fury G8	267800000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-11850H", "gpu": "16GB Nvidia Quadro RTX 5000", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "ندارد", "screen": "FHD IPS", "weight": "2.35", "storage": "512GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 7, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.533247	2026-09-03 23:32:29.833173	\N	[]	[]
63	1	9	laptop	2	Tecra A40-J	50100000	1	t	\N	\N	{"cpu": "i3 1115G4", "gpu": "INTEL UHD", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Toshiba", "screen": "FHD IPS Matte", "storage": "256GB SSD", "backlit_keyboard": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.592545	2026-09-03 09:32:29.452593	\N	[]	[]
65	1	9	laptop	4	MacBook Air 2017	50100000	1	t	\N	\N	{"cpu": "i5", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Apple", "screen": "FHD", "storage": "128GB SSD"}	PUBLISHED	2026-08-29 09:29:31.593038	2026-09-03 09:32:29.452648	لپتاپ MacBook Air 2017 یک لپتاپ سبک و قابل حمل برای دانشجویان، کارمندان و کاربرانی است که به دنبال یک دستگاه با عملکرد مناسب برای کارهای روزمره و بهره‌وری هستند. این مدل با پردازنده Intel i5 و حافظه SSD، تجربه‌ای سریع و روان را ارائه می‌دهد.	["پردازنده Intel Core i5 نسل هفتم", "۸ گیگابایت حافظه رم DDR3", "حافظه داخلی ۱۲۸ گیگابایت SSD", "صفحه نمایش ۱۴ اینچی با رزولوشن FHD", "گرافیک مجتمع Intel HD Graphics 6000", "طراحی باریک و سبک با وزن کم", "سیستم عامل macOS", "عمر باتری مناسب برای استفاده روزانه", "پورت‌های Thunderbolt 3 برای اتصال سریع", "بلندگوهای استریو با کیفیت", "کیبورد با نور پس‌زمینه", "حسگر اثر انگشت Touch ID"]	["عدم وجود پورت‌های USB-A", "حافظه داخلی نسبتاً کم"]
66	1	9	laptop	5	EliteDesk 800 G1 )مینی کیس(	17100000	2	t	\N	\N	{"cpu": "i5-4590", "gpu": "intel", "lte": "ندارد", "ram": "4GB", "x360": "ندارد", "brand": "HP", "screen": "-", "storage": "500GB HDD"}	PUBLISHED	2026-08-29 09:29:31.59314	2026-09-03 09:32:29.452672	\N	[]	[]
81	1	9	laptop	25	Surface Go 2 - 1824	30500000	2	t	\N	\N	{"dp": "ندارد", "cpu": "Pentium 4415y", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "FHD Touch", "weight": "0.54", "storage": "120GB SSD", "usb_ports": 0, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 09:29:31.59399	2026-09-03 23:32:28.74703	\N	[]	[]
87	1	9	laptop	33	Zbook Fury G8	244100000	1	t	\N	\N	{"cpu": "i7-11850H", "gpu": "16GB Nvidia Quadro RTX 5000", "ram": "16GB", "brand": "Hp", "screen": "17.3 FHD IPS", "storage": "512GB SSD"}	PUBLISHED	2026-08-29 09:29:31.594222	2026-09-03 06:10:39.489135	Zbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای اجرای برنامه‌های سنگین و کارهای خلاقانه ایده‌آل است. عملکرد بی‌نظیر و قابلیت اطمینان بالا، آن را به انتخابی مناسب برای محیط‌های حرفه‌ای تبدیل می‌کند.	["پردازنده Intel Core i7-11850H نسل یازدهم", "16 گیگابایت حافظه رم DDR4 با سرعت بالا", "حافظه داخلی 512 گیگابایت SSD NVMe", "کارت گرافیک Nvidia Quadro RTX 5000 با 16GB حافظه", "نمایشگر 17.3 اینچی FHD IPS با کیفیت بالا", "پنل IPS با رنگ‌های دقیق و زنده", "سیستم خنک‌کننده پیشرفته برای عملکرد پایدار", "بدنه مقاوم و مستحکم با طراحی صنعتی", "پورت‌های متنوع شامل USB-C، Thunderbolt و HDMI", "کیبورد با نور پس‌زمینه برای کار در محیط‌های کم نور", "پشتیبانی از فناوری‌های امنیتی پیشرفته", "مناسب برای رندرینگ، شبیه‌سازی و مدل‌سازی سه‌بعدی"]	["وزن نسبتاً زیاد", "عمر باتری محدود تحت بار سنگین"]
90	5	4	laptop	1	ProBook 4530S	27100000	1	t	87	\N	{"cpu": "i3-2310M", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "screen": "HD", "weight": "2.36", "storage": "120 SSD + 320HDD", "usb_ports": 4, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.530909	2026-09-03 09:32:53.599644	\N	[]	[]
91	5	4	laptop	2	Tecra A40-J	50100000	1	t	\N	\N	{"cpu": "i3 1115G4", "gpu": "INTEL UHD", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Toshiba", "screen": "FHD IPS Matte", "storage": "256GB SSD", "backlit_keyboard": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.531285	2026-09-03 09:32:53.599684	\N	[]	[]
93	5	4	laptop	4	MacBook Air 2017	50100000	1	t	\N	\N	{"cpu": "i5", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Apple", "screen": "FHD", "storage": "128GB SSD"}	PUBLISHED	2026-08-29 18:42:44.5315	2026-09-03 09:32:53.599737	\N	[]	[]
86	1	9	laptop	32	ThinkPad T540P	32900000	1	t	📝 ThinkPad T540P یک لپتاپ صنعتی قدرتمند برای انجام کارهای سنگین و برنامه‌نویسی است. با پردازنده قوی و کارت گرافیک مجزا، برای مهندسان و طراحان مناسب است. صفحه نمایش مات FHD، تجربه کاربری راحت‌تری ارائه می‌دهد.\n\n✅ مزایا:\n• پردازنده Intel Core i5 نسل چهارم\n• حافظه SSD 256 گیگابایتی\n• کارت گرافیک Nvidia GT730M\n• 8 گیگابایت رم DDR3\n• صفحه نمایش مات 15.6 اینچی\n\n⚠️ ملاحضات:\n• عمر باتری محدود\n• کارت گرافیک نسبتاً قدیمی	\N	{"cpu": "i5-4300M", "gpu": "1GB Nvidia GT730M", "ram": "8GB", "brand": "Lenovo", "screen": "15.6 FHD Matte", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 09:29:31.594186	2026-08-31 19:17:44.312759	\N	[]	[]
71	1	9	laptop	10	inspiron 3590	39100000	1	t	\N	\N	{"cpu": "i3-7100u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "FHD", "weight": "2.02", "storage": "256GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593605	2026-09-03 23:32:28.746877	\N	[]	[]
73	1	9	laptop	12	V130	44000000	1	t	\N	\N	{"cpu": "i5-7200u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "12GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Lenovo", "screen": "FHD", "weight": "1.8", "storage": "256GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593684	2026-09-03 23:32:28.746913	\N	[]	[]
75	1	9	laptop	16	Precision M6800	46400000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-4810MQ", "gpu": "2GB AMD Fire Pro 6100", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "dvd_rw": "دارد", "screen": "FHD Matte", "weight": "3.58", "storage": "128GB SSD +320GB HDD", "usb_ports": 4, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593769	2026-09-03 23:32:28.746938	\N	[]	[]
76	1	9	laptop	17	Probook 650 G8	81200000	2	t	\N	\N	{"dp": "ندارد", "cpu": "i5-1145G7", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "grade": "A++", "dvd_rw": "ندارد", "screen": "FHD", "weight": "1.74", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 6, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593807	2026-09-03 23:32:28.74695	Probook 650 G8 یک لپتاپ تجاری قدرتمند است که برای متخصصان و کاربران حرفه‌ای طراحی شده است. این لپتاپ با پردازنده نسل یازدهم اینتل و حافظه SSD سریع، عملکردی عالی برای کارهای روزمره و سنگین ارائه می‌دهد. ویژگی برجسته آن، وجود پورت Thunderbolt 4 است.	["پردازنده Intel Core i5-1145G7 نسل یازدهم", "حافظه رم ۸ گیگابایت DDR4", "حافظه داخلی ۲۵۶ گیگابایت SSD", "صفحه نمایش ۱۵.۶ اینچی با رزولوشن FHD (1920x1080)", "کارت گرافیک Intel Iris Xe Graphics", "پورت Thunderbolt 4 برای اتصال دستگاه‌های سریع", "دارای پورت HDMI برای اتصال به نمایشگر خارجی", "شبکه LAN با سرعت بالا برای اتصال سیمی", "حسگر اثر انگشت برای امنیت بیشتر"]	["عدم وجود درایو DVD-RW", "فاقد قابلیت پشتیبانی از قلم لمسی"]
108	5	4	laptop	21	ProBook 650 G1	32400000	1	t	\N	\N	{"dp": "دارد", "cpu": "i5-4300M", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "دارد", "screen": "HD", "weight": "2.32", "storage": "500GB HDD", "usb_ports": 5, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 5, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.533374	2026-09-03 23:32:29.833207	\N	[]	[]
82	1	9	laptop	26	Surface Laptop 3	73200000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i5-1035G7", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "2K Touch", "weight": "1.54", "storage": "256GB SSD", "usb_ports": 1, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 09:29:31.594028	2026-09-03 23:32:28.747042	\N	[]	[]
109	5	4	laptop	22	Zbook 17 G3	71400000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-6820HQ", "gpu": "2GB Nvidia QUADRO M1000m", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "HP", "dvd_rw": "ندارد", "screen": "inch fhd ips", "weight": "3", "storage": "512GB SSD", "usb_ports": 4, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 9, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.533486	2026-09-03 23:32:29.833239	\N	[]	[]
88	1	9	laptop	34	1900T	8600000	1	t	\N	\N	{"cpu": "-", "gpu": "-", "ram": "-", "brand": "Samsung", "screen": "LCD QHD 60HZ", "storage": "-"}	PENDING	2026-08-29 09:29:31.594258	2026-09-03 23:32:28.747246	\N	[]	[]
110	5	4	laptop	24	Surface Go 3 -1926	65300000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i3-10100y", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "FHD Touch", "weight": "0.54", "storage": "120GB SSD", "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 8, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.533591	2026-09-03 23:32:29.833273	\N	[]	[]
111	5	4	laptop	25	Surface Go 2 - 1824	30500000	2	t	\N	\N	{"dp": "ندارد", "cpu": "Pentium 4415y", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "FHD Touch", "weight": "0.54", "storage": "120GB SSD", "usb_ports": 0, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.533697	2026-09-03 23:32:29.833302	\N	[]	[]
112	5	4	laptop	26	Surface Laptop 3	73200000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i5-1035G7", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "2K Touch", "weight": "1.54", "storage": "256GB SSD", "usb_ports": 1, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.533805	2026-09-03 23:32:29.833341	\N	[]	[]
115	5	4	laptop	29	Surface Pro 5 LTE	44600000	1	t	صفحه ترک دارد	\N	{"cpu": "i5-7200u", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Microsoft", "screen": "2K Touch", "weight": "0.77", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 18:42:44.534136	2026-09-03 23:32:29.83343	\N	[]	[]
77	1	9	laptop	18	VJPJ11C11N	59800000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-8565u", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Sony Vaio", "dvd_rw": "ندارد", "screen": "FHD Ips 8BIT", "weight": "1.64", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 6, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593843	2026-09-03 23:32:28.746962	\N	[]	[]
78	1	9	laptop	19	Zbook G2	44000000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-4710 MQ", "gpu": "Nvidia Quadro K1100 2GB DDr5", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "ندارد", "screen": "FHD", "weight": "2.82", "storage": "256GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.59388	2026-09-03 23:32:28.746974	\N	[]	[]
79	1	9	laptop	22	Zbook 17 G3	71400000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-6820HQ", "gpu": "2GB Nvidia QUADRO M1000m", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "HP", "dvd_rw": "ندارد", "screen": "inch fhd ips", "weight": "3", "storage": "512GB SSD", "usb_ports": 4, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 9, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593917	2026-09-03 23:32:28.747008	\N	[]	[]
120	1	9	laptop	1	ProBook 4530S	27100000	1	t	87	\N	{"cpu": "i3-2310M", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "screen": "HD", "weight": "2.36", "storage": "120 SSD + 320HDD", "usb_ports": 4, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 19:29:13.64387	2026-09-03 09:32:29.45255	\N	[]	[]
80	1	9	laptop	24	Surface Go 3 -1926	65300000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i3-10100y", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "FHD Touch", "weight": "0.54", "storage": "120GB SSD", "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 8, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 09:29:31.593953	2026-09-03 23:32:28.747019	\N	[]	[]
117	5	4	laptop	31	ThinkPad T540P	36000000	1	t	\N	\N	{"dp": "دارد", "cpu": "i5-4300M", "gpu": "1GB Nvidia GT730M", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Lenovo", "dvd_rw": "دارد", "screen": "FHD Matte", "weight": "2.41", "storage": "256GB SSD", "usb_ports": 4, "fingerprint": "دارد", "pen_support": "دارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "دارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.534354	2026-09-03 23:32:29.833482	\N	[]	[]
121	1	9	laptop	20	Zbook Fury G8	267800000	1	t	\N	\N	{"dp": "دارد", "cpu": "i7-11850H", "gpu": "16GB Nvidia Quadro RTX 5000", "lan": "دارد", "lte": "ندارد", "ram": "16GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "ندارد", "screen": "FHD IPS", "weight": "2.35", "storage": "512GB SSD", "usb_ports": 3, "fingerprint": "دارد", "pen_support": "ندارد", "thunderbolt": "دارد", "battery_life": 7, "touch_screen": "ندارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 19:29:13.645345	2026-09-03 23:32:28.746985	Zbook Fury G8 یک لپتاپ ورک‌استیشن قدرتمند برای متخصصان گرافیک، طراحان و توسعه‌دهندگان است. با پردازنده قوی و کارت گرافیک حرفه‌ای، این لپتاپ برای کارهای سنگین و محاسبات پیچیده ایده‌آل است. صفحه نمایش بزرگ و باکیفیت، تجربه بصری بی‌نظیری را ارائه می‌دهد.	["پردازنده Intel Core i7-11850H نسل یازدهم", "۱۶ گیگابایت رم DDR4 برای اجرای همزمان برنامه‌ها", "حافظه SSD با ظرفیت ۵۱۲ گیگابایت با سرعت بالا", "کارت گرافیک Nvidia Quadro RTX 5000 با ۱۶ گیگابایت حافظه", "صفحه نمایش ۱۷.۳ اینچی FHD IPS با کیفیت تصویر عالی", "پورت‌های Thunderbolt برای اتصال دستگاه‌های سریع", "دارای پورت LAN برای اتصال با سیم", "وب‌کم با قابلیت تشخیص چهره (Facial Recognition)", "کیبورد با نور پس زمینه (Backlit Keyboard)", "حسگر اثر انگشت (Fingerprint) برای امنیت بیشتر", "دارای پورت‌های USB متعدد", "عمر باتری تا ۷ ساعت"]	["وزن نسبتاً زیاد (۲.۳۵ کیلوگرم)", "عدم وجود درایو DVD-RW"]
122	1	9	laptop	21	ProBook 650 G1	32400000	1	t	\N	\N	{"dp": "دارد", "cpu": "i5-4300M", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Hp", "dvd_rw": "دارد", "screen": "HD", "weight": "2.32", "storage": "500GB HDD", "usb_ports": 5, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 5, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 19:29:13.645505	2026-09-03 23:32:28.746996	لپتاپ ProBook 650 G1 یک گزینه مناسب برای کاربران حرفه‌ای و دانشجویان است که به دنبال یک دستگاه قابل اعتماد و با کارایی برای انجام وظایف روزمره و محاسبات متوسط هستند. این لپتاپ با پردازنده Intel Core i5 و هارد درایو 500 گیگابایتی، عملکرد قابل قبولی را ارائه می‌دهد.	["پردازنده Intel Core i5-4300M برای کارهای روزمره", "حافظه رم 8 گیگابایت برای اجرای همزمان برنامه‌ها", "هارد درایو 500 گیگابایتی برای ذخیره‌سازی حجم زیادی از داده", "صفحه نمایش 15.6 اینچی HD برای دیدن راحت محتوا", "پورت DisplayPort برای اتصال به مانیتورهای خارجی", "پورت LAN برای اتصال به شبکه‌های سیمی", "درایو DVD-RW برای خواندن و نوشتن دیسک‌های نوری", "پنج پورت USB برای اتصال انواع دستگاه‌های جانبی", "وزن 2.32 کیلوگرم، نسبتاً قابل حمل", "عمر باتری تا 5 ساعت در استفاده معمولی", "طراحی مقاوم و بادوام", "مناسب برای استفاده‌های اداری و تحصیلی"]	["گرافیک مجتمع Intel", "عدم وجود صفحه نمایش لمسی"]
118	5	4	laptop	34	1900T	8600000	1	t	\N	\N	{"cpu": "-", "gpu": "-", "ram": "-", "brand": "Samsung", "screen": "LCD QHD 60HZ", "storage": "-"}	PUBLISHED	2026-08-29 18:42:44.534439	2026-09-03 23:32:29.833508	\N	[]	[]
123	1	9	laptop	30	Surface Pro 5	58000000	1	t	با کیبورد بلوتوثی نو	\N	{"cpu": "i5-7200u", "gpu": "intel", "lte": "دارد", "ram": "8GB", "x360": "ندارد", "brand": "Microsoft", "screen": "2K Touch", "weight": "0.77", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 19:29:13.645894	2026-09-03 23:32:28.747191	Surface Pro 5، یک تبلت/لپتاپ ۲-در-۱ قدرتمند با پردازنده نسل هفتم اینتل و حافظه SSD سریع. این دستگاه با امکان اتصال LTE و همراه داشتن کیبورد بلوتوثی، یک ابزار ایده‌آل برای کارهای سیار و بهره‌وری در هر مکانی است.	["پردازنده Intel Core i5-7200U نسل هفتم", "۸ گیگابایت حافظه رم DDR4", "۲۵۶ گیگابایت حافظه SSD سریع", "صفحه نمایش لمسی ۲K با کیفیت بالا (12.5 اینچ)", "اتصال LTE برای اینترنت پرسرعت در هر مکان", "وزن سبک و قابل حمل (۰.۷۷ کیلوگرم)", "سیستم عامل ویندوز 10 Pro", "گرافیک مجتمع Intel HD Graphics 620", "پورت USB 3.0 برای انتقال سریع داده"]	["عمر باتری متوسط", "پورت‌های محدود"]
124	1	9	laptop	31	ThinkPad T540P	36000000	1	t	\N	\N	{"dp": "دارد", "cpu": "i5-4300M", "gpu": "1GB Nvidia GT730M", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Lenovo", "dvd_rw": "دارد", "screen": "FHD Matte", "weight": "2.41", "storage": "256GB SSD", "usb_ports": 4, "fingerprint": "دارد", "pen_support": "دارد", "thunderbolt": "ندارد", "battery_life": 2, "touch_screen": "دارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 19:29:13.646029	2026-09-03 23:32:28.747221	ThinkPad T540P یک لپتاپ قدرتمند و بادوام برای متخصصان و کاربران حرفه‌ای است که به دنبال عملکرد بالا در یک بدنه مقاوم می‌باشند. این مدل با پردازنده Intel Core i5 و گرافیک Nvidia، برای کارهای محاسباتی سنگین و برنامه‌های کاربردی مختلف مناسب است. صفحه نمایش مات Full HD آن، تجربه بصری راحت و بدون بازتاب را فراهم می‌کند.	["پردازنده Intel Core i5-4300M", "حافظه رم 8GB DDR3", "حافظه SSD با ظرفیت 256GB", "کارت گرافیک Nvidia GT730M با 1GB حافظه", "صفحه نمایش 15.6 اینچی Full HD Matte", "درایو نوری DVD-RW", "پورت DisplayPort برای اتصال مانیتور خارجی", "چهار پورت USB برای اتصال دستگاه‌های جانبی", "حسگر اثر انگشت برای امنیت بیشتر", "پشتیبانی از قلم نوری (Pen Support)", "وزن نسبتاً سبک 2.41 کیلوگرم", "کیبورد با نور پس زمینه ندارد"]	["عمر باتری محدود (2 ساعت)", "عدم وجود پورت HDMI"]
64	1	9	laptop	3	1215N Mini	15900000	1	t	بدون باتری	\N	{"cpu": "Athom-D525", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "6GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Asus", "screen": "HD", "weight": "1.5", "storage": "500GB HDD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.592892	2026-09-03 09:32:29.452623	لپتاپ 1215N Mini ایسوس، یک گزینه سبک و قابل حمل برای کارهای روزمره و دانشجویی است. با وجود عدم باتری، این مدل برای استفاده در محیط‌های ثابت مانند دفتر کار یا خانه ایده‌آل است و امکان اتصال به برق را به صورت مداوم فراهم می‌کند. این لپتاپ با پردازنده اتم و هارددیسک 500 گیگابایتی، نیازهای اساسی شما را برآورده می‌کند.	["پردازنده Intel Atom D525 برای کاربری سبک", "رم 6 گیگابایت برای اجرای همزمان برنامه‌ها", "هارددیسک 500 گیگابایتی فضای ذخیره‌سازی کافی", "صفحه نمایش HD با کیفیت تصویر مناسب", "پورت LAN برای اتصال به شبکه سیمی", "خروجی HDMI برای اتصال به نمایشگر خارجی", "سه پورت USB برای اتصال لوازم جانبی", "وزن سبک 1.5 کیلوگرمی برای حمل آسان", "طراحی فشرده و جمع‌وجور", "مناسب برای کارهای متنی و وب‌گردی", "سیستم عامل ویندوز (پیش‌فرض)", "قابلیت ارتقاء رم (بررسی با سازنده)"]	["عدم وجود باتری", "گرافیک مجتمع اینتل"]
67	1	9	laptop	6	Latitude e6520	23200000	3	t	با باتری نو با گارانتی ۴ ماهه + ۲ تومان	\N	{"cpu": "i5-2220m", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "8GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Dell", "screen": "HD", "weight": "2.5", "storage": "120GB SSD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "battery_life": 3, "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 09:29:31.593239	2026-09-03 23:32:28.74683	\N	[]	[]
68	1	9	laptop	7	inspiron 7567 Gaming	95200000	1	t	\N	\N	{"cpu": "i7-7700HQ", "gpu": "Nvidia GTX 1050TI 4GB DDr5", "lte": "ندارد", "ram": "16GB", "brand": "Dell", "screen": "UHD 4K IPS Matte", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 09:29:31.593355	2026-09-03 23:32:28.746852	\N	[]	[]
69	1	9	laptop	8	Precision M6800	47600000	1	t	\N	\N	{"cpu": "i7-4810MQ", "gpu": "2GB Nvidia Quadro K3100", "lte": "ندارد", "ram": "16GB", "x360": "ندارد", "brand": "Dell", "dvd_rw": "دارد", "screen": "FHD Matte", "storage": "128GB SSD +320GB HDD", "pen_support": "ندارد", "touch_screen": "ندارد", "backlit_keyboard": "دارد"}	PUBLISHED	2026-08-29 09:29:31.593454	2026-09-03 23:32:28.746865	\N	[]	[]
72	1	9	laptop	11	ProBook 450 G6	52500000	0	f	\N	\N	{"cpu": "i5-8250u", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "HP", "screen": "FHD", "weight": "2", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 09:29:31.593645	2026-09-03 23:32:28.746901	\N	[]	[]
92	5	4	laptop	3	1215N Mini	15900000	1	t	بدون باتری	\N	{"cpu": "Athom-D525", "gpu": "intel", "lan": "دارد", "lte": "ندارد", "ram": "6GB", "hdmi": "دارد", "x360": "ندارد", "brand": "Asus", "screen": "HD", "weight": "1.5", "storage": "500GB HDD", "usb_ports": 3, "fingerprint": "ندارد", "pen_support": "ندارد", "thunderbolt": "ندارد", "touch_screen": "ندارد", "backlit_keyboard": "ندارد", "facial_recognition": "ندارد"}	PUBLISHED	2026-08-29 18:42:44.531399	2026-09-03 09:32:53.599714	\N	[]	[]
94	5	4	laptop	5	EliteDesk 800 G1 )مینی کیس(	17100000	2	t	\N	\N	{"cpu": "i5-4590", "gpu": "intel", "lte": "ندارد", "ram": "4GB", "x360": "ندارد", "brand": "HP", "screen": "-", "storage": "500GB HDD"}	PUBLISHED	2026-08-29 18:42:44.531599	2026-09-03 09:32:53.599762	\N	[]	[]
102	5	4	laptop	13	Tecra A40-J	59800000	3	t	\N	\N	{"cpu": "i5-1135 G7", "gpu": "intel", "lte": "ندارد", "ram": "8GB", "x360": "ندارد", "brand": "Toshiba", "screen": "FHD Touch Matte", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 18:42:44.532571	2026-09-03 23:32:29.833094	\N	[]	[]
89	1	9	laptop	35	2233SN	9800000	1	t	📝 لپتاپ 2233SN سامسونگ، یک انتخاب ایده‌آل برای دانشجویان و کاربران خانگی است که به دنبال یک دستگاه با کارایی مناسب و برند معتبر هستند. این مدل با قابلیت‌های متنوع، برای انجام کارهای روزمره و سرگرمی طراحی شده است.\n\n✅ مزایا:\n• کیفیت ساخت قابل قبول سامسونگ\n• صفحه نمایش با رزولوشن مناسب\n• وزن نسبتاً سبک برای حمل\n• امکانات ارتباطی کامل\n• قیمت رقابتی در بازار\n\n⚠️ ملاحضات:\n• مشخصات فنی پایه برای پردازش\n• عدم وجود کارت گرافیک مجزا	\N	{"cpu": "-", "gpu": "-", "ram": "-", "brand": "Samsung", "screen": "LCD FHD / 60HZ", "storage": "-"}	PENDING	2026-08-29 09:29:31.594293	2026-09-03 23:32:28.747269	لپتاپ 2233SN سامسونگ، گزینه‌ای مقرون‌به‌صرفه برای انجام امور روزمره، تکالیف دانشجویی و سرگرمی‌های سبک است. با تکیه بر کیفیت ساخت سامسونگ و صفحه نمایش باکیفیت، تجربه‌ای قابل قبول را برای کاربران خانگی و دانش‌آموزان ارائه می‌دهد. این لپتاپ با وزن نسبتاً سبک و امکانات ارتباطی کامل، برای استفاده‌های متغیر مناسب است.	["صفحه نمایش 21.5 اینچی LCD", "رزولوشن Full HD (1920x1080)", "نرخ تازه‌سازی 60 هرتز", "کیفیت تصویر مناسب برای محتوای استاندارد", "بدنه مقاوم و بادوام", "وزن سبک برای حمل و نقل آسان", "پورت‌های متنوع (USB، HDMI، و غیره)", "وب‌کم و میکروفون داخلی", "پشتیبانی از Wi-Fi و بلوتوث", "سیستم عامل از پیش نصب شده (ویندوز)", "باتری با طول عمر متوسط"]	["پردازنده گرافیکی یکپارچه", "حافظه و رم محدود"]
113	5	4	laptop	27	Surface Laptop 3	83600000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-1065g7", "gpu": "intel", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "2K Touch", "weight": "1.54", "storage": "256GB SSD", "usb_ports": 1, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 5, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.53391	2026-09-03 23:32:29.833374	\N	[]	[]
114	5	4	laptop	28	Surface Book 2	103700000	1	t	\N	\N	{"dp": "ندارد", "cpu": "i7-8650u", "gpu": "2GB Nvidia GTX 1050", "lan": "ندارد", "lte": "ندارد", "ram": "16GB", "hdmi": "ندارد", "x360": "ندارد", "brand": "Microsoft", "dvd_rw": "ندارد", "screen": "4K Touch", "weight": "1.64", "storage": "512GB SSD", "usb_ports": 2, "fingerprint": "ندارد", "pen_support": "دارد", "thunderbolt": "دارد", "battery_life": 8, "touch_screen": "دارد", "backlit_keyboard": "دارد", "facial_recognition": "دارد"}	PUBLISHED	2026-08-29 18:42:44.534015	2026-09-03 23:32:29.833398	\N	[]	[]
116	5	4	laptop	30	Surface Pro 5	58000000	1	t	با کیبورد بلوتوثی نو	\N	{"cpu": "i5-7200u", "gpu": "intel", "lte": "دارد", "ram": "8GB", "x360": "ندارد", "brand": "Microsoft", "screen": "2K Touch", "weight": "0.77", "storage": "256GB SSD"}	PUBLISHED	2026-08-29 18:42:44.534242	2026-09-03 23:32:29.833457	\N	[]	[]
119	5	4	laptop	35	2233SN	9800000	1	t	\N	\N	{"cpu": "-", "gpu": "-", "ram": "-", "brand": "Samsung", "screen": "LCD FHD / 60HZ", "storage": "-"}	PUBLISHED	2026-08-29 18:42:44.534553	2026-09-03 23:32:29.833532	\N	[]	[]
\.


--
-- Data for Name: subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscriptions (id, customer_id, plan_key, status, start_at, end_at, grace_end_at, created_at) FROM stdin;
1	1	BRONZE	ACTIVE	2026-08-23 00:53:28.379547	2026-09-22 00:53:28.379547	2026-09-24 00:53:28.379547	2026-08-23 00:53:17.442901
3	1	GOLD	ACTIVE	2026-08-23 21:46:26.049313	2026-09-22 21:46:26.049313	2026-09-24 21:46:26.049313	2026-08-23 21:45:55.633315
6	5	GOLD	EXPIRED	2026-08-28 23:01:22.837323	2026-08-28 23:03:30.339455	2026-09-11 23:01:22.837323	2026-08-28 23:01:22.841046
4	4	GOLD	EXPIRED	2026-08-23 22:23:42.378762	2026-08-31 09:53:43.400339	2026-09-24 22:23:42.378762	2026-08-23 22:23:31.45663
7	5	GOLD	EXPIRED	2026-08-28 23:03:35.045445	2026-09-03 08:28:11.925312	2026-09-11 23:03:35.045445	2026-08-28 23:03:35.04946
8	5	GOLD	ACTIVE	2026-09-03 08:28:30.91815	2026-10-03 08:28:30.91815	2026-10-10 08:28:30.91815	2026-09-03 08:28:30.923583
\.


--
-- Data for Name: tutorials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tutorials (id, key, title, category, content_type, text_content, video_file_id, video_caption, display_order, is_active, faq_question, created_at, updated_at) FROM stdin;
4	connect_sheet	📊 اتصال Google Sheet	sheet	text	📊 <b>اتصال Google Sheet</b>\n━━━━━━━━━━━━━━━\n\nبا اتصال Google Sheet، قیمت و موجودی محصولات\nبه صورت خودکار آپدیت می‌شن.\n\n<b>روش پیشنهادی:</b>\n\n1️⃣ از منوی '📊 اتصال Google Sheet'\nدکمه '📥 دریافت لینک شیت نمونه' رو بزنید\n\n2️⃣ روی لینک کلیک کنید (باز میشه توی Google Sheets)\n\n3️⃣ دکمه <b>Make a copy</b> رو بزنید\nیه کپی در Google Drive شما ساخته میشه\n\n4️⃣ محصولات خودتون رو در صفحه‌های مربوطه وارد کنید\n\n5️⃣ دکمه ی فایل رو در بالای صفحه بزنید و به عنوان سند Google Sheet ذخیره کنید\n\n6️⃣ دکمه <b>Share</b> بالای شیت رو بزنید\n\n7️⃣ ایمیل ربات رو اضافه کنید با دسترسی <b>Editor</b>\n\n8️⃣ لینک شیت رو کپی کنید\n\n9️⃣ برگردید به ربات و دکمه '➕ اتصال Google Sheet'\nلینک رو بفرستید.\n\n🔟 برای اولین همگام‌سازی، دکمه '🔃 همگام‌سازی الان' رو بزنید.\n\n✅ از این به بعد سیستم خودکار (هر ۲ ساعت) شیت شما رو چک می‌کنه!	\N	\N	1	t	\N	2026-08-23 00:41:48.821238	2026-09-04 14:49:49.94638
5	using_ai	🤖 استفاده از هوش مصنوعی	ai	text	🤖 <b>استفاده از هوش مصنوعی</b>\n━━━━━━━━━━━━━━━\n\nAI می‌تونه توضیحات جذاب برای محصولات شما بنویسه.\n\n<b>روش‌های استفاده:</b>\n\n1️⃣ <b>دستی (هر محصول جداگانه)</b>\nاز منوی '📦 مدیریت محصولات' یه محصول انتخاب کنید\nو دکمه '🤖 تولید توضیحات با AI' رو بزنید.\n\n2️⃣ <b>خودکار (هنگام ارسال)</b>\nاز منوی '⚙️ تنظیمات' → 'AI خودکار' رو فعال کنید.\nهنگام ارسال خودکار، AI برای محصولات بدون توضیحات\nخودش متن تولید می‌کنه.\n\n<b>هزینه:</b>\n• هر تولید = ۱ توکن AI\n• توکن ماهانه با پلن پرو رایگان\n• توکن اضافی از منوی '🤖 توکن AI' قابل خرید\n\n<b>نکات:</b>\n• AI ممکنه گاهی اشتباه کنه\n• قبل از ارسال، پیش‌نمایش رو ببینید\n• متن‌های AI بعد از تولید ذخیره می‌شن	\N	\N	1	t	\N	2026-08-23 00:41:48.841955	2026-09-04 14:49:49.955357
6	faq_bot_admin	FAQ - ادمین کانال	faq	faq	❓ <b>چرا ربات نمی‌تونه پست بذاره؟</b>\n\nمعمولاً یکی از این دلایله:\n\n1️⃣ ربات ادمین کانال نیست\n→ ربات رو ادمین کانال کنید\n\n2️⃣ دسترسی Post Messages نداره\n→ توی تنظیمات ادمین، این دسترسی رو فعال کنید\n\n3️⃣ کانال Private و ربات دعوت نشده\n→ ربات رو به کانال اضافه کنید\n\n4️⃣ اشتراک منقضی شده\n→ از منوی اشتراک تمدید کنید	\N	\N	1	t	چرا ربات نمیتونه پست بذاره؟	2026-08-23 00:41:48.862576	2026-09-04 14:49:49.965247
7	faq_price_update	FAQ - آپدیت قیمت	faq	faq	❓ <b>قیمت‌ها چطور آپدیت می‌شن؟</b>\n\nدو راه دارید:\n\n1️⃣ <b>Google Sheet (خودکار)</b>\nقیمت رو در شیت تغییر بدید، هر ۲ ساعت خودکار آپدیت میشه.\nپست‌های قبلی توی کانال هم ویرایش میشن.\n\n2️⃣ <b>فایل اکسل جدید</b>\nفایل اکسل با قیمت‌های جدید آپلود کنید.\nمحصولاتی که SKU یکسان دارن، آپدیت میشن.\n\n⚠️ توجه:\n• محصولات جدید (SKU جدید) اضافه میشن\n• محصولات موجود آپدیت میشن\n• پست‌های قبلی توی کانال ویرایش میشن (نه پست جدید)	\N	\N	2	t	قیمت‌ها چطور آپدیت می‌شن؟	2026-08-23 00:41:48.887719	2026-09-04 14:49:49.975934
2	connect_channel	📢 نحوه اتصال کانال	channel	video	📢 <b>اتصال کانال تلگرام</b>\n━━━━━━━━━━━━━━━\n\nبرای اتصال کانال این مراحل رو انجام دهید:\n\n1️⃣ به کانال خود برید\n\n2️⃣ روی نام کانال کلیک کنید\n\n3️⃣ گزینه <b>Administrators</b> را انتخاب کنید\n\n4️⃣ دکمه <b>Add Administrator</b>\n\n5️⃣ ربات ما رو جستجو و انتخاب کنید\n\n6️⃣ حتماً دسترسی <b>Post Messages</b> رو فعال کنید\n\n7️⃣ به ربات برگردید و از منوی '📢 مدیریت کانال'\nآیدی کانال رو بفرستید:\nمثال: @your_channel\nیا: -100123456789\n\n⚠️ <b>نکته مهم:</b>\nاگه ربات ادمین کانال نباشه، اتصال ناموفقه.	BAACAgQAAxkBAAIB5Gpos9AiGNtk0BhOTRo8Y8gnPn0zAAJlIAACFXhIU1JlJ3Pk3OYgPQQ	🎬 راهنمای اتصال کانال به ربات	1	t	\N	2026-08-23 00:41:48.775673	2026-09-04 14:49:49.897997
3	upload_excel	📤 آپلود فایل اکسل	upload	text	📤 <b>آپلود فایل اکسل</b>\n━━━━━━━━━━━━━━━\n\n1️⃣ <b>دانلود فایل نمونه</b>\nاز منوی '📤 آپلود محصولات' دکمه '📥 دانلود فایل نمونه' رو بزنید.\n\n2️⃣ <b>پر کردن فایل</b>\nفایل شامل چند صفحه (Sheet) است:\n├── laptops (لپتاپ‌ها)\n├── prebuilt_pcs (کیس‌های آماده)\n├── monitors (مانیتورها)\n├── components (قطعات)\n└── accessories (لوازم جانبی)\n\nمحصولات هر دسته رو در صفحه مربوطه وارد کنید.\n\n3️⃣ <b>نکات مهم فایل</b>\n• نام صفحه‌ها و ستون‌ها رو تغییر نده\n• کد محصول باید یکتا باشه\n• قیمت به تومان و فقط عدد\n• موجودی: عدد (0 = ناموجود)\n• صفحه‌های خالی مشکلی نداره\n\n4️⃣ <b>ارسال فایل</b>\nدکمه '📤 ارسال فایل اکسل' رو بزنید و فایل رو ارسال کنید.\n\n5️⃣ <b>نتیجه</b>\nربات فایل رو پردازش می‌کنه و خلاصه‌ای از نتیجه بهتون می‌ده.	\N	\N	1	t	\N	2026-08-23 00:41:48.797544	2026-09-04 14:49:49.93774
8	faq_expired_subscription	FAQ - انقضای اشتراک	faq	faq	❓ <b>بعد از انقضای اشتراک چی میشه؟</b>\n\n📅 <b>۵ روز قبل انقضا:</b>\nیادآوری اول ارسال میشه.\n\n📅 <b>۱ روز قبل انقضا:</b>\nیادآوری فوری ارسال میشه.\n\n📅 <b>روز انقضا:</b>\nسرویس متوقف میشه، ولی ۲ روز مهلت تمدید دارید.\nپست‌های قبلی حذف نمیشن.\n\n📅 <b>۲ روز بعد انقضا (پایان مهلت):</b>\nحساب معلق میشه، ولی همه داده‌ها حفظ میشن.\nبرای فعال‌سازی مجدد با پشتیبانی تماس بگیرید.	\N	\N	3	t	بعد از انقضای اشتراک چی میشه؟	2026-08-23 00:41:48.910631	2026-09-04 14:49:49.984326
1	getting_started	🚀 شروع سریع	general	text	🚀 <b>شروع سریع با ربات</b>\n━━━━━━━━━━━━━━━\n\nبرای استفاده از ربات این ۴ قدم رو انجام دهید:\n\n1️⃣ <b>خرید اشتراک</b>\nاز منوی '💳 اشتراک من' یک پلن مناسب انتخاب کنید.\n\n2️⃣ <b>اتصال کانال تلگرام</b>\nربات رو ادمین کانال کنید و از منوی '📢 مدیریت کانال' اتصال بدید.\n\n3️⃣ <b>آپلود محصولات</b>\nفایل اکسل نمونه رو دانلود کنید، پر کنید و آپلود کنید.\n(یا Google Sheet متصل کنید)\n\n4️⃣ <b>تنظیم ارسال خودکار</b>\nاز منوی '⚙️ تنظیمات' حالت خودکار رو فعال کنید.\n\n💡 برای هر مرحله راهنمای جداگانه در همین بخش موجوده.	\N	\N	1	t	\N	2026-08-23 00:41:48.731446	2026-09-04 14:49:49.869663
\.


--
-- Name: account_link_codes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.account_link_codes_id_seq', 7, true);


--
-- Name: ai_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ai_tokens_id_seq', 7, true);


--
-- Name: ai_usage_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ai_usage_logs_id_seq', 61, true);


--
-- Name: business_mapping_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.business_mapping_profiles_id_seq', 1, true);


--
-- Name: businesses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.businesses_id_seq', 11, true);


--
-- Name: channels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.channels_id_seq', 9, true);


--
-- Name: customers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.customers_id_seq', 6, true);


--
-- Name: google_sheet_connections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.google_sheet_connections_id_seq', 9, true);


--
-- Name: post_template_presets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.post_template_presets_id_seq', 3, true);


--
-- Name: post_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.post_templates_id_seq', 2, true);


--
-- Name: posted_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.posted_messages_id_seq', 147, true);


--
-- Name: posting_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.posting_settings_id_seq', 9, true);


--
-- Name: product_platform_media_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.product_platform_media_id_seq', 20, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.products_id_seq', 124, true);


--
-- Name: subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.subscriptions_id_seq', 8, true);


--
-- Name: tutorials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tutorials_id_seq', 8, true);


--
-- Name: account_link_codes account_link_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_link_codes
    ADD CONSTRAINT account_link_codes_pkey PRIMARY KEY (id);


--
-- Name: ai_tokens ai_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_tokens
    ADD CONSTRAINT ai_tokens_pkey PRIMARY KEY (id);


--
-- Name: ai_usage_logs ai_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT ai_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: business_mapping_profiles business_mapping_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_mapping_profiles
    ADD CONSTRAINT business_mapping_profiles_pkey PRIMARY KEY (id);


--
-- Name: businesses businesses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT businesses_pkey PRIMARY KEY (id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: google_sheet_connections google_sheet_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_sheet_connections
    ADD CONSTRAINT google_sheet_connections_pkey PRIMARY KEY (id);


--
-- Name: post_template_presets post_template_presets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_template_presets
    ADD CONSTRAINT post_template_presets_pkey PRIMARY KEY (id);


--
-- Name: post_templates post_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_templates
    ADD CONSTRAINT post_templates_pkey PRIMARY KEY (id);


--
-- Name: posted_messages posted_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posted_messages
    ADD CONSTRAINT posted_messages_pkey PRIMARY KEY (id);


--
-- Name: posting_settings posting_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_settings
    ADD CONSTRAINT posting_settings_pkey PRIMARY KEY (id);


--
-- Name: product_platform_media product_platform_media_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_platform_media
    ADD CONSTRAINT product_platform_media_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: tutorials tutorials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tutorials
    ADD CONSTRAINT tutorials_pkey PRIMARY KEY (id);


--
-- Name: products uq_customer_sku; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT uq_customer_sku UNIQUE (customer_id, sku);


--
-- Name: posted_messages uq_product_channel; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posted_messages
    ADD CONSTRAINT uq_product_channel UNIQUE (product_id, channel_id);


--
-- Name: product_platform_media uq_product_platform_media_order; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_platform_media
    ADD CONSTRAINT uq_product_platform_media_order UNIQUE (product_id, platform, media_order);


--
-- Name: ix_account_link_codes_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_account_link_codes_customer_id ON public.account_link_codes USING btree (customer_id);


--
-- Name: ix_account_link_codes_link_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_account_link_codes_link_code ON public.account_link_codes USING btree (link_code);


--
-- Name: ix_ai_tokens_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ai_tokens_customer_id ON public.ai_tokens USING btree (customer_id);


--
-- Name: ix_ai_usage_logs_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ai_usage_logs_customer_id ON public.ai_usage_logs USING btree (customer_id);


--
-- Name: ix_business_mapping_profiles_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_business_mapping_profiles_customer_id ON public.business_mapping_profiles USING btree (customer_id);


--
-- Name: ix_businesses_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_businesses_customer_id ON public.businesses USING btree (customer_id);


--
-- Name: ix_channels_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_channels_customer_id ON public.channels USING btree (customer_id);


--
-- Name: ix_customers_bale_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customers_bale_user_id ON public.customers USING btree (bale_user_id);


--
-- Name: ix_customers_telegram_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customers_telegram_user_id ON public.customers USING btree (telegram_user_id);


--
-- Name: ix_google_sheet_connections_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_google_sheet_connections_customer_id ON public.google_sheet_connections USING btree (customer_id);


--
-- Name: ix_post_template_presets_business_type_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_post_template_presets_business_type_key ON public.post_template_presets USING btree (business_type_key);


--
-- Name: ix_post_template_presets_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_post_template_presets_is_active ON public.post_template_presets USING btree (is_active);


--
-- Name: ix_post_template_presets_subcategory_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_post_template_presets_subcategory_key ON public.post_template_presets USING btree (subcategory_key);


--
-- Name: ix_post_templates_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_post_templates_customer_id ON public.post_templates USING btree (customer_id);


--
-- Name: ix_posted_messages_channel_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_posted_messages_channel_id ON public.posted_messages USING btree (channel_id);


--
-- Name: ix_posted_messages_product_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_posted_messages_product_id ON public.posted_messages USING btree (product_id);


--
-- Name: ix_posting_settings_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_posting_settings_customer_id ON public.posting_settings USING btree (customer_id);


--
-- Name: ix_product_platform_media_product_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_product_platform_media_product_id ON public.product_platform_media USING btree (product_id);


--
-- Name: ix_products_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_products_customer_id ON public.products USING btree (customer_id);


--
-- Name: ix_subscriptions_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subscriptions_customer_id ON public.subscriptions USING btree (customer_id);


--
-- Name: ix_tutorials_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tutorials_category ON public.tutorials USING btree (category);


--
-- Name: ix_tutorials_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tutorials_key ON public.tutorials USING btree (key);


--
-- Name: account_link_codes account_link_codes_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_link_codes
    ADD CONSTRAINT account_link_codes_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: ai_tokens ai_tokens_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_tokens
    ADD CONSTRAINT ai_tokens_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: ai_usage_logs ai_usage_logs_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT ai_usage_logs_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: ai_usage_logs ai_usage_logs_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT ai_usage_logs_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: business_mapping_profiles business_mapping_profiles_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_mapping_profiles
    ADD CONSTRAINT business_mapping_profiles_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: businesses businesses_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT businesses_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: channels channels_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: customers customers_selected_post_preset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_selected_post_preset_id_fkey FOREIGN KEY (selected_post_preset_id) REFERENCES public.post_template_presets(id);


--
-- Name: google_sheet_connections google_sheet_connections_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_sheet_connections
    ADD CONSTRAINT google_sheet_connections_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: post_templates post_templates_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.post_templates
    ADD CONSTRAINT post_templates_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: posted_messages posted_messages_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posted_messages
    ADD CONSTRAINT posted_messages_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id);


--
-- Name: posted_messages posted_messages_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posted_messages
    ADD CONSTRAINT posted_messages_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: posting_settings posting_settings_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_settings
    ADD CONSTRAINT posting_settings_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: product_platform_media product_platform_media_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_platform_media
    ADD CONSTRAINT product_platform_media_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: products products_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id);


--
-- Name: products products_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: subscriptions subscriptions_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- PostgreSQL database dump complete
--

\unrestrict TYBGK8GkvQX2MnLn8eKO0zhfkGoyxJWun4RofarQNMICZcj7rebfCGZDPjta03O

