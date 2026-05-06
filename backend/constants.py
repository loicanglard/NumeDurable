DIFFICULTES = ["facile", "moyen", "difficile", "expert"]
TYPES_PRATIQUE = ["trail", "vtt", "rando", "ski_rando"]
STATUTS = ["praticable", "partiel", "ferme"]
OBSTACLES = ["neige", "boue", "verglas", "arbre_tombe", "crue", "travaux", "autre"]
NIVEAUX = ["débutant", "intermédiaire", "expert"]

# Flash message categories (standardized to avoid typos like 'succes')
FLASH_SUCCESS = 'success'
FLASH_ERROR = 'error'
FLASH_INFO = 'info'


def get_limiter():
    """Récupère l'instance limiter si disponible, sinon retourne un dummy."""
    try:
        from backend import limiter, LIMITER_AVAILABLE
        if LIMITER_AVAILABLE and limiter:
            return limiter
    except:
        pass
    
    # Retourner un dummy limiter qui ne fait rien
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    
    return DummyLimiter()