from flask import current_app


def resolve_user_table_name(supabase):
    """Resolve whether the auth table is named `user` or `users`.

    Caches the result on app config to avoid repeated probing.
    """
    cached = current_app.config.get('SUPABASE_USER_TABLE')
    if cached in ('user', 'users'):
        return cached

    # Try singular first (matches local SQL schema), then plural (common Supabase schema).
    for candidate in ('user', 'users'):
        try:
            supabase.table(candidate).select('id').limit(1).execute()
            current_app.config['SUPABASE_USER_TABLE'] = candidate
            return candidate
        except Exception:
            continue

    # Keep behavior predictable if both probes fail.
    current_app.config['SUPABASE_USER_TABLE'] = 'users'
    return 'users'


def user_table(supabase):
    return supabase.table(resolve_user_table_name(supabase))
