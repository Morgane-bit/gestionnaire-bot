-- ============================================================
-- GESTIONNAIRE BOT - Script de création des tables Supabase
-- Colle ce script dans l'éditeur SQL de ton projet Supabase
-- ============================================================

-- Table des utilisateurs
create table if not exists users (
  id bigint primary key,
  name text not null,
  profile text check (profile in ('particulier', 'commercant')),
  revenu_mensuel numeric default 0,
  created_at timestamp with time zone default now()
);

-- Table des dépenses (module particulier)
create table if not exists depenses (
  id uuid default gen_random_uuid() primary key,
  user_id bigint references users(id) on delete cascade,
  montant numeric not null,
  categorie text not null,
  description text default '',
  date date default current_date,
  created_at timestamp with time zone default now()
);

-- Table des ventes (module commerçant)
create table if not exists ventes (
  id uuid default gen_random_uuid() primary key,
  user_id bigint references users(id) on delete cascade,
  produit text not null,
  quantite int not null default 1,
  prix_unitaire numeric not null,
  date date default current_date,
  created_at timestamp with time zone default now()
);

-- Table des stocks (module commerçant)
create table if not exists stocks (
  id uuid default gen_random_uuid() primary key,
  user_id bigint references users(id) on delete cascade,
  produit text not null,
  quantite int not null default 0,
  seuil_alerte int default 5,
  prix_vente numeric default 0,
  updated_at timestamp with time zone default now(),
  unique(user_id, produit)
);

-- Index pour améliorer les performances
create index if not exists idx_depenses_user_date on depenses(user_id, date);
create index if not exists idx_ventes_user_date on ventes(user_id, date);
create index if not exists idx_stocks_user on stocks(user_id);

-- Migration Phase 3 : ajouter prix_achat aux stocks
alter table stocks add column if not exists prix_achat numeric default 0;
