-- Function to execute dynamic SQL queries
CREATE OR REPLACE FUNCTION execute_sql(query text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    result json;
BEGIN
    -- Log the query being executed
    RAISE LOG 'Executing query: %', query;
    
    -- Execute the query and convert result to JSON
    EXECUTE format('SELECT json_agg(t) FROM (%s) t', query) INTO result;
    
    -- Return empty array if null
    RETURN COALESCE(result, '[]'::json);
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error
        RAISE LOG 'Error executing query: % - Error: %', query, SQLERRM;
        -- Re-raise the error
        RAISE EXCEPTION 'Error executing SQL query: %', SQLERRM;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION execute_sql(text) TO authenticated; 