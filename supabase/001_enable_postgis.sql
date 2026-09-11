-- Run once in the Supabase SQL Editor before starting the backend.
create extension if not exists postgis;
create extension if not exists "uuid-ossp";

select postgis_full_version();
