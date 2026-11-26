"""What the settings page reads besides the values: the order of the definitions, units, dependencies"""


def test_index_keeps_the_definition_order(client, auth_headers, make_user):
    import application.models.setting as settingModel
    user = make_user("settings-reader@test.local")

    response = client.get("/instance/settings/index", headers=auth_headers(user))

    assert response.status_code == 200
    by_position = sorted(response.json, key=lambda name: response.json[name]["position"])
    assert by_position == list(settingModel.setting_configuration)


def test_dependencies_name_an_existing_switch():
    import application.models.setting as settingModel
    for name, config in settingModel.setting_configuration.items():
        if "depends_on" in config:
            switch = settingModel.setting_configuration.get(config["depends_on"])
            assert switch is not None and switch["type"] == "checkbox", name


def test_numbers_have_a_unit_and_a_valid_range():
    import application.models.setting as settingModel
    for name, config in settingModel.setting_configuration.items():
        if config["type"] != "number":
            continue
        assert config.get("unit"), name
        assert config.get("min", float("-inf")) <= config["default"] <= config.get("max", float("inf")), name
        if "min_nonzero" in config:
            assert config["min"] == 0 and config.get("zero_text"), name
            assert config["min_nonzero"] <= config["max"], name
