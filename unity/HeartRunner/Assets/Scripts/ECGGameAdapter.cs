using UnityEngine;

public class ECGGameAdapter : MonoBehaviour
{
    [Header("Vitesse du jeu")]
    public float vitesseNormale = 1f;

    private GameManager gameManager;

    void Start()
    {
        gameManager = FindObjectOfType<GameManager>();
    }

    void Update()
    {
        AdapterJeu();
    }

    void AdapterJeu()
    {
        string action = PythonConnector.ActionJeu;

        switch (action)
        {
            case "continuer_normal":
                // Cœur normal → jeu normal
                Time.timeScale = vitesseNormale;
                break;

            case "ralentir_jeu":
                // Tachycardie → jeu ralentit
                Time.timeScale = vitesseNormale * 0.6f;
                break;

            case "pause_respiration":
                // Très élevé → jeu très lent
                Time.timeScale = vitesseNormale * 0.3f;
                break;

            case "mode_securise":
                // Danger → jeu pause
                Time.timeScale = 0f;
                break;

            default:
                Time.timeScale = vitesseNormale;
                break;
        }
    }

    void OnDestroy()
    {
        // Remet la vitesse normale quand on quitte
        Time.timeScale = 1f;
    }
}