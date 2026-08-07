"""Schémas transverses réutilisables."""

from pydantic import BaseModel


class Page[T](BaseModel):
    """Page de résultats paginés (limit/offset).

    - `total`  : nombre total d'éléments correspondant au filtre.
    - `items`  : éléments de la page courante.
    - `limit`  : taille de page demandée.
    - `offset` : décalage depuis le début.
    """

    total: int
    items: list[T]
    limit: int
    offset: int
