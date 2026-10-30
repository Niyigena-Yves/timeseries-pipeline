CREATE DATABASE IF NOT EXISTS african_crises;
USE african_crises;

CREATE TABLE IF NOT EXISTS countries (
	cc3 CHAR(3) PRIMARY KEY,
	name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS annual_observations (
	id BIGINT PRIMARY KEY AUTO_INCREMENT,
	country_cc3 CHAR(3) NOT NULL,
	year SMALLINT NOT NULL,
	case_number INT NULL,
	exch_usd DOUBLE NOT NULL,
	gdp_weighted_default DOUBLE NOT NULL,
	inflation_annual_cpi DOUBLE NOT NULL,
	CONSTRAINT uq_observation_country_year UNIQUE (country_cc3, year),
	CONSTRAINT fk_observation_country FOREIGN KEY (country_cc3)
		REFERENCES countries (cc3) ON DELETE CASCADE,
	INDEX ix_observation_year_country (year, country_cc3),
	INDEX ix_observation_country_year (country_cc3, year)
);

CREATE TABLE IF NOT EXISTS crisis_indicators (
	id BIGINT PRIMARY KEY AUTO_INCREMENT,
	observation_id BIGINT NOT NULL UNIQUE,
	systemic_crisis TINYINT NOT NULL,
	domestic_debt_in_default TINYINT NOT NULL,
	sovereign_external_debt_default TINYINT NOT NULL,
	independence TINYINT NOT NULL,
	currency_crises TINYINT NOT NULL,
	inflation_crises TINYINT NOT NULL,
	banking_crisis TINYINT NOT NULL,
	CONSTRAINT fk_crisis_observation FOREIGN KEY (observation_id)
		REFERENCES annual_observations (id) ON DELETE CASCADE,
	INDEX ix_crisis_banking (banking_crisis)
);
