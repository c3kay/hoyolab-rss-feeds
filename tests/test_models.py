from hoyolabrssfeeds import models
import pytest

# -- NOTE: This module does only test custom methods for pydantic models! --


def test_item_category_from_str(category: models.FeedItemCategory) -> None:
    cat = models.FeedItemCategory.from_str(category.name)
    assert cat == category


def test_invalid_category_str() -> None:
    with pytest.raises(ValueError):
        models.FeedItemCategory.from_str("Invalid")


def test_game_from_str(game: models.Game) -> None:
    g = models.Game.from_str(game.name)
    assert g == game


def test_invalid_game_str() -> None:
    with pytest.raises(ValueError):
        models.Game.from_str("Invalid")
