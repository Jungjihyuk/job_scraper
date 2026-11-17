-- 실제 DB(job_scraper_db)의 스키마 스냅샷. lantern scan이 schema.dbml과 비교하는 기준이다.
-- 손으로 고치지 않는다. 마이그레이션을 실제 DB에 적용한 뒤 다시 만든다:
--   docker exec job_scraper_postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only --no-owner --no-privileges --exclude-table=alembic_version' | grep -v '^\\(un\)\?restrict' > backend/app/db/schema.sql
--
-- PostgreSQL database dump
--


-- Dumped from database version 18.6 (Debian 18.6-1.pgdg13+2)
-- Dumped by pg_dump version 18.6 (Debian 18.6-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.companies (
    company_id integer NOT NULL,
    company_name character varying(255) NOT NULL,
    company_type character varying(50),
    company_size character varying(50),
    company_type_labels jsonb,
    ai_confidence double precision,
    source_info jsonb,
    is_listed boolean,
    listing_market character varying(20),
    stock_code character varying(20),
    blind_registered boolean,
    blind_avg_rating numeric(2,1),
    blind_career_rating numeric(2,1),
    blind_worklife_rating numeric(2,1),
    blind_welfare_rating numeric(2,1),
    blind_culture_rating numeric(2,1),
    blind_management_rating numeric(2,1),
    blind_last_updated timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: companies_company_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.companies_company_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: companies_company_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.companies_company_id_seq OWNED BY public.companies.company_id;


--
-- Name: core_tech_review_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.core_tech_review_staging (
    id integer NOT NULL,
    posting_id character varying(100) NOT NULL,
    reviewed_technologies jsonb,
    ai_predicted_technologies jsonb,
    reviewer_note text,
    annotation_id integer,
    reviewed_at timestamp without time zone,
    status character varying(20) DEFAULT 'pending'::character varying,
    taxonomy_version character varying(20) DEFAULT '1.0.0'::character varying NOT NULL
);


--
-- Name: core_tech_review_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.core_tech_review_staging_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: core_tech_review_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.core_tech_review_staging_id_seq OWNED BY public.core_tech_review_staging.id;


--
-- Name: domain_review_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.domain_review_staging (
    id integer NOT NULL,
    posting_id character varying(100) NOT NULL,
    reviewed_domain character varying(100),
    ai_predicted_domain character varying(100),
    reviewer_note text,
    annotation_id integer,
    reviewed_at timestamp without time zone,
    status character varying(20) DEFAULT 'pending'::character varying,
    taxonomy_version character varying(20) DEFAULT '1.0.0'::character varying NOT NULL
);


--
-- Name: domain_review_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.domain_review_staging_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: domain_review_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.domain_review_staging_id_seq OWNED BY public.domain_review_staging.id;


--
-- Name: experience_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experience_categories (
    experience_category_id integer NOT NULL,
    raw_experience character varying(100) NOT NULL,
    standardized_experience character varying(50),
    min_years integer,
    max_years integer,
    is_fresh_welcome boolean,
    confidence numeric(3,2),
    matching_method character varying(50),
    manual_review boolean,
    correction character varying(50),
    review_note text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: experience_categories_experience_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.experience_categories_experience_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: experience_categories_experience_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.experience_categories_experience_category_id_seq OWNED BY public.experience_categories.experience_category_id;


--
-- Name: job_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_categories (
    job_category_id integer NOT NULL,
    job_category character varying(100) NOT NULL,
    job_field character varying(100) NOT NULL,
    job_specialty character varying(100),
    scraper_type character varying(50) NOT NULL
);


--
-- Name: job_categories_job_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_categories_job_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_categories_job_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_categories_job_category_id_seq OWNED BY public.job_categories.job_category_id;


--
-- Name: job_posting; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_posting (
    id integer NOT NULL,
    posting_id character varying(100) NOT NULL,
    original_url character varying(2048),
    job_category_id integer NOT NULL,
    company_id integer NOT NULL,
    location_id integer NOT NULL,
    experience_category_id integer,
    experience character varying(50),
    "position" character varying(255),
    position_detail text,
    main_tasks text,
    requirements text,
    preferred text,
    benefits text,
    tags json,
    hiring_process text,
    deadline date,
    is_always_recruiting boolean,
    domain_l1 character varying(50),
    domain_l2 character varying(100),
    domain_l3 character varying(200),
    specialty_l1 character varying(50),
    specialty_l2 character varying(100),
    employment_type character varying(30),
    core_technologies jsonb,
    taxonomy_version character varying(20),
    posted_date timestamp without time zone,
    normalization_failed boolean DEFAULT false NOT NULL
);


--
-- Name: job_posting_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_posting_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_posting_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_posting_id_seq OWNED BY public.job_posting.id;


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    location_id integer NOT NULL,
    location character varying(100) NOT NULL,
    location_detail character varying(255),
    region character varying(20)
);


--
-- Name: locations_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.locations_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: locations_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.locations_location_id_seq OWNED BY public.locations.location_id;


--
-- Name: scraped_urls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scraped_urls (
    id integer NOT NULL,
    batch_id integer NOT NULL,
    url character varying(2048) NOT NULL,
    url_hash character varying(64) NOT NULL,
    status character varying(20) NOT NULL,
    retry_count integer,
    error_message text,
    scraped_at timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: scraped_urls_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scraped_urls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scraped_urls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scraped_urls_id_seq OWNED BY public.scraped_urls.id;


--
-- Name: scraping_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scraping_batches (
    id integer NOT NULL,
    batch_name character varying(255) NOT NULL,
    scraper_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    total_urls integer,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    collected_count integer DEFAULT 0 NOT NULL,
    saved_count integer DEFAULT 0 NOT NULL,
    failed_count integer DEFAULT 0 NOT NULL,
    skipped_count integer DEFAULT 0 NOT NULL
);


--
-- Name: scraping_batches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scraping_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scraping_batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scraping_batches_id_seq OWNED BY public.scraping_batches.id;


--
-- Name: scraping_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scraping_tasks (
    id integer NOT NULL,
    batch_id integer NOT NULL,
    task_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    success_count integer,
    fail_count integer,
    retry_count integer,
    max_retries integer,
    started_at timestamp without time zone,
    duration integer,
    error_message text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: scraping_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scraping_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scraping_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scraping_tasks_id_seq OWNED BY public.scraping_tasks.id;


--
-- Name: companies company_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies ALTER COLUMN company_id SET DEFAULT nextval('public.companies_company_id_seq'::regclass);


--
-- Name: core_tech_review_staging id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.core_tech_review_staging ALTER COLUMN id SET DEFAULT nextval('public.core_tech_review_staging_id_seq'::regclass);


--
-- Name: domain_review_staging id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain_review_staging ALTER COLUMN id SET DEFAULT nextval('public.domain_review_staging_id_seq'::regclass);


--
-- Name: experience_categories experience_category_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experience_categories ALTER COLUMN experience_category_id SET DEFAULT nextval('public.experience_categories_experience_category_id_seq'::regclass);


--
-- Name: job_categories job_category_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_categories ALTER COLUMN job_category_id SET DEFAULT nextval('public.job_categories_job_category_id_seq'::regclass);


--
-- Name: job_posting id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting ALTER COLUMN id SET DEFAULT nextval('public.job_posting_id_seq'::regclass);


--
-- Name: locations location_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations ALTER COLUMN location_id SET DEFAULT nextval('public.locations_location_id_seq'::regclass);


--
-- Name: scraped_urls id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_urls ALTER COLUMN id SET DEFAULT nextval('public.scraped_urls_id_seq'::regclass);


--
-- Name: scraping_batches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraping_batches ALTER COLUMN id SET DEFAULT nextval('public.scraping_batches_id_seq'::regclass);


--
-- Name: scraping_tasks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraping_tasks ALTER COLUMN id SET DEFAULT nextval('public.scraping_tasks_id_seq'::regclass);


--
-- Name: companies companies_company_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_company_name_key UNIQUE (company_name);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (company_id);


--
-- Name: core_tech_review_staging core_tech_review_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.core_tech_review_staging
    ADD CONSTRAINT core_tech_review_staging_pkey PRIMARY KEY (id);


--
-- Name: core_tech_review_staging core_tech_review_staging_posting_id_annotation_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.core_tech_review_staging
    ADD CONSTRAINT core_tech_review_staging_posting_id_annotation_id_key UNIQUE (posting_id, annotation_id);


--
-- Name: domain_review_staging domain_review_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain_review_staging
    ADD CONSTRAINT domain_review_staging_pkey PRIMARY KEY (id);


--
-- Name: domain_review_staging domain_review_staging_posting_id_annotation_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain_review_staging
    ADD CONSTRAINT domain_review_staging_posting_id_annotation_id_key UNIQUE (posting_id, annotation_id);


--
-- Name: experience_categories experience_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experience_categories
    ADD CONSTRAINT experience_categories_pkey PRIMARY KEY (experience_category_id);


--
-- Name: experience_categories experience_categories_raw_experience_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experience_categories
    ADD CONSTRAINT experience_categories_raw_experience_key UNIQUE (raw_experience);


--
-- Name: job_categories job_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_categories
    ADD CONSTRAINT job_categories_pkey PRIMARY KEY (job_category_id);


--
-- Name: job_posting job_posting_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_pkey PRIMARY KEY (id);


--
-- Name: job_posting job_posting_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_posting_id_key UNIQUE (posting_id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (location_id);


--
-- Name: scraped_urls scraped_urls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_urls
    ADD CONSTRAINT scraped_urls_pkey PRIMARY KEY (id);


--
-- Name: scraped_urls scraped_urls_url_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_urls
    ADD CONSTRAINT scraped_urls_url_hash_key UNIQUE (url_hash);


--
-- Name: scraping_batches scraping_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraping_batches
    ADD CONSTRAINT scraping_batches_pkey PRIMARY KEY (id);


--
-- Name: scraping_tasks scraping_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraping_tasks
    ADD CONSTRAINT scraping_tasks_pkey PRIMARY KEY (id);


--
-- Name: job_categories unique_job_combination; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_categories
    ADD CONSTRAINT unique_job_combination UNIQUE (job_category, job_field, job_specialty);


--
-- Name: locations unique_location_combination; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT unique_location_combination UNIQUE (location, location_detail);


--
-- Name: idx_companies_listing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_listing ON public.companies USING btree (is_listed, listing_market);


--
-- Name: idx_companies_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_name ON public.companies USING btree (company_name);


--
-- Name: idx_companies_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_type ON public.companies USING btree (company_type);


--
-- Name: idx_experience_fresh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_experience_fresh ON public.experience_categories USING btree (is_fresh_welcome);


--
-- Name: idx_experience_standardized; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_experience_standardized ON public.experience_categories USING btree (standardized_experience);


--
-- Name: idx_experience_years; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_experience_years ON public.experience_categories USING btree (min_years, max_years);


--
-- Name: idx_job_posting_always_recruiting; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_always_recruiting ON public.job_posting USING btree (is_always_recruiting);


--
-- Name: idx_job_posting_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_category ON public.job_posting USING btree (job_category_id);


--
-- Name: idx_job_posting_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_company ON public.job_posting USING btree (company_id);


--
-- Name: idx_job_posting_deadline; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_deadline ON public.job_posting USING btree (deadline);


--
-- Name: idx_job_posting_domain_l1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_domain_l1 ON public.job_posting USING btree (domain_l1);


--
-- Name: idx_job_posting_domain_l2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_domain_l2 ON public.job_posting USING btree (domain_l2);


--
-- Name: idx_job_posting_employment_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_employment_type ON public.job_posting USING btree (employment_type);


--
-- Name: idx_job_posting_experience; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_experience ON public.job_posting USING btree (experience_category_id);


--
-- Name: idx_job_posting_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_location ON public.job_posting USING btree (location_id);


--
-- Name: idx_job_posting_posted_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_posted_date ON public.job_posting USING btree (posted_date);


--
-- Name: idx_job_posting_specialty_l1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_specialty_l1 ON public.job_posting USING btree (specialty_l1);


--
-- Name: idx_job_posting_specialty_l2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_specialty_l2 ON public.job_posting USING btree (specialty_l2);


--
-- Name: idx_job_posting_taxonomy_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_posting_taxonomy_version ON public.job_posting USING btree (taxonomy_version);


--
-- Name: idx_locations_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_region ON public.locations USING btree (region);


--
-- Name: idx_scraped_urls_batch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraped_urls_batch ON public.scraped_urls USING btree (batch_id);


--
-- Name: idx_scraped_urls_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraped_urls_hash ON public.scraped_urls USING btree (url_hash);


--
-- Name: idx_scraped_urls_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraped_urls_status ON public.scraped_urls USING btree (status);


--
-- Name: idx_scraping_batches_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraping_batches_status ON public.scraping_batches USING btree (status);


--
-- Name: idx_scraping_batches_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraping_batches_type ON public.scraping_batches USING btree (scraper_type);


--
-- Name: idx_scraping_tasks_batch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraping_tasks_batch ON public.scraping_tasks USING btree (batch_id);


--
-- Name: job_posting job_posting_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id);


--
-- Name: job_posting job_posting_experience_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_experience_category_id_fkey FOREIGN KEY (experience_category_id) REFERENCES public.experience_categories(experience_category_id);


--
-- Name: job_posting job_posting_job_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_job_category_id_fkey FOREIGN KEY (job_category_id) REFERENCES public.job_categories(job_category_id);


--
-- Name: job_posting job_posting_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_posting
    ADD CONSTRAINT job_posting_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(location_id);


--
-- Name: scraped_urls scraped_urls_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_urls
    ADD CONSTRAINT scraped_urls_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.scraping_batches(id);


--
-- Name: scraping_tasks scraping_tasks_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraping_tasks
    ADD CONSTRAINT scraping_tasks_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.scraping_batches(id);


--
-- PostgreSQL database dump complete
--


