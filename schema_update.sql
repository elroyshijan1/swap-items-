-- Run this once against swapshelf_db to add login support
-- to your existing Members table.

USE swapshelf_db;

ALTER TABLE Members
  ADD COLUMN Email VARCHAR(255) UNIQUE,
  ADD COLUMN PasswordHash VARCHAR(255);

-- Your 6 existing members will have NULL Email/PasswordHash.
-- They can't log in until you either:
--   a) register new accounts through the website, or
--   b) manually set Email for them and have them use "Forgot setup"
--      (not built here) / re-register.
-- Easiest: just register fresh accounts via /register for testing.
