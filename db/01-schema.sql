CREATE DATABASE IF NOT EXISTS animeverse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE animeverse;
CREATE TABLE IF NOT EXISTS anime (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(500) NOT NULL,
 score DECIMAL(4,2),
 popularity INT,
 genres TEXT,
 studios TEXT,
 type VARCHAR(100),
 year INT,
 episodes INT,
 themes TEXT,
 demographic VARCHAR(200),
 members BIGINT,
 synopsis TEXT,
 features TEXT,
 FULLTEXT KEY ft_name_genres (name,genres,studios)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
