BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Phone" VARCHAR(255), 
	"Type" VARCHAR(255), 
	"Industry" VARCHAR(255), 
	"Name" VARCHAR(255), 
	PRIMARY KEY (id)
);
-- No sample data inserted due to Litify PM validation rule conflicts
-- Litify PM requires Account names to satisfy a "last name" validation rule
COMMIT;
