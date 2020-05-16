-- based on https://github.com/cieszynski/sqlite-nested-sets/blob/master/nested_set.sql

-- main table
CREATE TABLE sarafan_comments (
	id INTEGER primary key,
	publication_magnet TEXT,
	post_magnet TEXT NOT NULL,
	content TEXT NOT NULL,
	lft INTEGER,
	rgt INTEGER,
	parent INTEGER,
	UNIQUE(publication_magnet),
	FOREIGN KEY (post_magnet) REFERENCES sarafan_posts(magnet),
	FOREIGN KEY (publication_magnet) REFERENCES sarafan_publications(magnet)
);

-- helper table to store variable
CREATE TABLE p (
	id	INTEGER primary key,
	rgt	INTEGER,
	lft	INTEGER
);

---- init table
--INSERT INTO sarafan_comments (id,name,lft,rgt) VALUES (1, 'root',1,2);

-- trigger to insert, move or delete item/subtree
-- to insert new item: fields name and parent are required
CREATE TRIGGER insert_item AFTER INSERT ON sarafan_comments
WHEN New.parent is not null
BEGIN
	UPDATE sarafan_comments SET lft=(SELECT rgt FROM sarafan_comments WHERE id=New.parent),
					            rgt=(SELECT rgt FROM sarafan_comments WHERE id=New.parent)+1
		WHERE id IS NEW.id;
	UPDATE sarafan_comments SET lft=lft+2 WHERE publication_magnet = New.publication_magnet AND lft > (SELECT rgt FROM sarafan_comments WHERE id=NEW.parent) AND id IS NOT NEW.id;
	UPDATE sarafan_comments SET rgt=rgt+2 WHERE publication_magnet = New.publication_magnet AND rgt >= (SELECT rgt FROM sarafan_comments WHERE id=NEW.parent) AND id IS NOT NEW.id;
END;

-- after item is removed: recalculating the tree
CREATE TRIGGER delete_item AFTER DELETE ON sarafan_comments
BEGIN
    DELETE FROM sarafan_comments WHERE publication_magnet = OLD.publication_magnet AND lft BETWEEN OLD.lft AND OLD.rgt;
    UPDATE sarafan_comments SET lft=lft-round((OLD.rgt-OLD.lft+1)) WHERE publication_magnet = OLD.publication_magnet AND lft > OLD.rgt;
    UPDATE sarafan_comments SET rgt=rgt-round((OLD.rgt-OLD.lft+1)) WHERE publication_magnet = OLD.publication_magnet AND rgt > OLD.rgt;
END;
