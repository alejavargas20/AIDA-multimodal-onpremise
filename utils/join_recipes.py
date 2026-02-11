def recipe_desembolso__cierre() -> str:
    return "FROM cartera.desembolso d INNER JOIN cartera.cierre c ON c.idCuenta = d.idCuenta"

def recipe_desembolso__cosecha_sal() -> str:
    return (
        "FROM cartera.desembolso d "
        "INNER JOIN rcc.cosecha_sal cs "
        "ON cs.idCliente = d.idCliente AND cs.nCosecha = d.nCosecha"
    )

def recipe_cliente__cuentas_activas() -> str:
    return (
        "WITH CuentasActivas AS ("
        "  SELECT DISTINCT idCuenta FROM cartera.cierre "
        "  WHERE idCliente = @IdCliente AND nStock = @UltimoMes"
        ") "
    )

def recipe_cuentas_activas__comportamiento() -> str:
    return (
        "FROM cartera.desembolso_comportamiento dc "
        "INNER JOIN CuentasActivas ca ON ca.idCuenta = dc.idCuentaVig"
    )
