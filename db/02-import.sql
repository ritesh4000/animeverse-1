USE animeverse;
LOAD DATA LOCAL INFILE '/docker-entrypoint-initdb.d/anime.csv'
INTO TABLE anime
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(name,score,popularity,genres,studios,type,year,episodes,themes,demographic,members,synopsis,features);
