-- Run this in the Supabase SQL editor to set up storage for HalluciGuard AI.

create extension if not exists "pgcrypto";

create table if not exists scans (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  response text not null,
  result jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists scans_created_at_idx on scans (created_at desc);
