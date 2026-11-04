(() => {
    const cronometros = document.querySelectorAll(
        ".tm-time[data-iniciado-ms]"
    );

    cronometros.forEach((elemento) => {
        // Impede que o mesmo elemento receba dois intervalos.
        if (elemento.dataset.timerAtivo === "1") return;

        elemento.dataset.timerAtivo = "1";

        const inicio = Number(elemento.dataset.iniciadoMs);

        const atualizar = () => {
            if (!elemento.isConnected) {
                clearInterval(intervalo);
                return;
            }

            const segundos = Math.max(
                0,
                (Date.now() - inicio) / 1000
            );

            elemento.textContent = `◷ ${segundos.toFixed(2)} s`;
        };

        const intervalo = setInterval(atualizar, 100);

        atualizar();
    });
})();
