/**
    Publication
*/
create table sarafan_publications (
    magnet text primary key,
    source text not null,
    size integer not null,
    reply_to text,
    retention integer
);
create index idx_sarafan_publication_source on sarafan_publications (source);
create index idx_sarafan_publication_reply_to on sarafan_publications (reply_to);

/**
    Post
*/
create table sarafan_posts (
    magnet text primary key,
    content text not null
);

/**
    Peer
*/
create table sarafan_peers(
    hostname text primary key,
    created_at integer default CURRENT_TIMESTAMP,
    rating real default 0.5,
    last_seen integer default CURRENT_TIMESTAMP
);
create unique index idx_sarafan_peer_hostname on sarafan_peers (hostname);
