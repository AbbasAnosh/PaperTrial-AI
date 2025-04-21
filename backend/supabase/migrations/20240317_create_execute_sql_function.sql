-- This migration creates the execute_sql function which is required for running migrations.
-- IMPORTANT: This function must be created manually in the Supabase dashboard before running migrations.
-- The migration script will detect this file and prompt you to create the function manually.

-- The function definition is provided below for reference:
/*
create or replace function execute_sql(sql text)
returns void
language plpgsql
as $$
begin
  execute sql;
end;
$$;

-- Grant execute permission to authenticated users
grant execute on function execute_sql(text) to authenticated;
*/

-- This file is intentionally empty to avoid circular dependency.
-- The actual function creation should be done manually in the Supabase dashboard. 