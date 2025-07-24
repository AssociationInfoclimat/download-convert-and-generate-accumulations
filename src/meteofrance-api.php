<?php

declare(strict_types=1);

namespace Infoclimat\MeteoFrance\API;

use Closure;
use Exception;

class CurlResponse
{
    public int          $code;
    public string|false $response;
    public array        $headers    = [];
    public int          $error_code = 0;
    public string       $error      = '';

    public function __construct(
        int          $code,
        false|string $response,
        array        $headers = [],
        int          $error_code = 0,
        string       $error = ''
    ) {
        $this->code = $code;
        $this->response = $response;
        $this->headers = $headers;
        $this->error_code = $error_code;
        $this->error = $error;
    }

    public function getJSON(): ?array
    {
        return json_decode($this->response, true);
    }
}

function get_headers_callback(array &$headers): Closure
{
    return function ($curl, $header) use (&$headers) {
        $key_value = explode(':', $header, 2);
        if (count($key_value) < 2) {
            return strlen($header);
        }
        [$key, $value] = $key_value;
        $key = trim($key);
        $value = trim($value);
        $headers[$key] = $value;
        return strlen($header);
    };
}

/**
 * @param string[] $headers
 */
function curl(
    string $url,
    array  $data = [],
    array  $headers = [],
    array  $options = []
): CurlResponse {
    $curl = curl_init($url);
    $options[CURLOPT_HTTPHEADER] = $headers;
    $options[CURLOPT_RETURNTRANSFER] = true;
    $headers = [];
    $options[CURLOPT_HEADERFUNCTION] = get_headers_callback($headers);
    if ($data) {
        $options[CURLOPT_POST] = true;
        $options[CURLOPT_POSTFIELDS] = $data;
    }
    curl_setopt_array($curl, $options);
    $response = curl_exec($curl);
    $code = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    $error_code = curl_errno($curl);
    $error = curl_error($curl);
    $curl_response = new CurlResponse(
        $code,
        $response,
        $headers,
        $error_code,
        $error
    );
    curl_close($curl);
    return $curl_response;
}

/**
 * @param string[] $headers
 */
function fetch_headers(
    string $url,
    array  $headers = [],
    array  $options = []
): array {
    $context = stream_context_create([
        'http' => [
                'method' => 'HEAD',
                'header' => $headers,
            ] + $options,
    ]);
    return get_headers($url, true, $context);
}

/**
 * @param string[] $headers
 */
function fetch(
    string $url,
    array  $headers = [],
    array  $options = []
): CurlResponse {
    return curl(
        $url,
        [],
        $headers,
        $options
    );
}

/**
 * @param string[] $headers
 */
function post(
    string $url,
    array  $data = [],
    array  $headers = [],
    array  $options = []
): CurlResponse {
    return curl(
        $url,
        $data,
        $headers,
        $options
    );
}

/**
 * @param string[] $headers
 */
function fetch_json(
    string $url,
    array  $headers = [],
    array  $options = []
): array {
    $curl_response = fetch($url, $headers, $options);
    return $curl_response->getJSON();
}

/**
 * @param string[] $headers
 */
function post_json(
    string $url,
    array  $data = [],
    array  $headers = [],
    array  $options = []
): array {
    $curl_response = post($url, $data, $headers, $options);
    return $curl_response->getJSON();
}

/**
 * @param string[] $headers
 */
function download_file(
    string $path,
    string $url,
    array  $headers = [],
    array  $options = []
): CurlResponse {
    $resource = fopen($path, 'w');
    $curl = curl_init($url);
    $response_headers = [];
    curl_setopt_array(
        $curl,
        $options + [
            CURLOPT_HTTPHEADER     => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FILE           => $resource,
            CURLOPT_HEADERFUNCTION => get_headers_callback($response_headers),
        ]
    );
    curl_exec($curl);
    $code = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    $response = '';
    $error_code = curl_errno($curl);
    $error = curl_error($curl);
    $curl_response = new CurlResponse(
        $code,
        $response,
        $response_headers,
        $error_code,
        $error
    );
    curl_close($curl);
    fclose($resource);
    return $curl_response;
}

class MeteoFranceAPI
{
    public static string $token = '';

    /**
     * @throws Exception
     */
    public static function updateToken(): void
    {
        MeteoFranceAPI::$token = fetch_token();
    }

    /**
     * @throws Exception
     */
    public static function ensureToken(): void
    {
        if (!MeteoFranceAPI::$token) {
            MeteoFranceAPI::updateToken();
        }
    }
}

/**
 * @throws Exception
 */
function fetch_token(): string
{
    $data = ['grant_type' => 'client_credentials'];
    $application_id = getenv('APPLICATION_ID');
    if (empty($application_id)) {
        throw new Exception('Missing APPLICATION_ID in environment variables');
    }
    $headers = ["Authorization: Basic {$application_id}"];
    $curl_response = post('https://portail-api.meteofrance.fr/token', $data, $headers);
    if ($curl_response->error) {
        throw new Exception($curl_response->error);
    }
    $json = $curl_response->getJSON();
    return $json['access_token'];
}

function is_token_expired(CurlResponse $curl_response, bool $downloading = false): bool
{
    if ($curl_response->code != 401) {
        return false;
    }
    if ($downloading) {
        return true;
    }
    $json = $curl_response->getJSON();
    if (!$json || !is_array($json)) {
        return false;
    }
    if (!array_key_exists('message', $json)) {
        return false;
    }
    return $json['message'] === 'Invalid Credentials';
}

/**
 * @param string[] $headers
 * @throws Exception
 */
function fetch_api_headers(
    string $url,
    array  $headers = [],
    array  $options = []
): array {
    if (!MeteoFranceAPI::$token) {
        MeteoFranceAPI::updateToken();
    }
    // TODO: Handle token expiration
    $headers[] = 'Authorization: Bearer ' . MeteoFranceAPI::$token;
    return fetch_headers($url, $headers, $options);
}

/**
 * @param string[] $headers
 * @throws Exception
 */
function fetch_api(
    string $url,
    array  $headers = [],
    array  $options = []
): string {
    if (!MeteoFranceAPI::$token) {
        MeteoFranceAPI::updateToken();
    }
    $headers[] = 'Authorization: Bearer ' . MeteoFranceAPI::$token;
    $curl_response = fetch($url, $headers, $options);
    if (!is_token_expired($curl_response)) {
        return $curl_response->response;
    }
    MeteoFranceAPI::updateToken();
    $curl_response = fetch($url, $headers, $options);
    return $curl_response->response;
}

/**
 * @param string[] $headers
 * @throws Exception
 */
function fetch_api_json(
    string $url,
    array  $headers = [],
    array  $options = []
): array {
    $json = fetch_api($url, $headers, $options);
    return json_decode($json, true);
}

function download_file_using_token(
    string $path,
    string $url,
    array  $headers = [],
    array  $options = []
): CurlResponse {
    $headers[] = 'Authorization: Bearer ' . MeteoFranceAPI::$token;
    return download_file(
        $path,
        $url,
        $headers,
        $options
    );
}

/**
 * @param string[] $headers
 * @throws Exception
 */
function download_api_file(
    string $path,
    string $url,
    array  $headers = [],
    array  $options = []
): CurlResponse {
    MeteoFranceAPI::ensureToken();
    $curl_response = download_file_using_token($path, $url, $headers, $options);
    if (!is_token_expired($curl_response, true)) {
        return $curl_response;
    }
    MeteoFranceAPI::updateToken();
    return download_file_using_token($path, $url, $headers, $options);
}

interface APIFileDownloader
{
    public function downloadAPIFile(
        string $path,
        string $url,
        array  $headers = [],
        array  $options = []
    ): CurlResponse;
}

class RealAPIFileDownloader implements APIFileDownloader
{
    /**
     * @throws Exception
     */
    public function downloadAPIFile(
        string $path,
        string $url,
        array  $headers = [],
        array  $options = []
    ): CurlResponse {
        return download_api_file($path, $url, $headers, $options);
    }
}

class InMemoryAPIFileDownloader implements APIFileDownloader
{
    public array $requests = [];

    /**
     * @var CurlResponse[]
     */
    private array $responses;

    /**
     * @param CurlResponse[] $responses
     */
    public function __construct(array $responses)
    {
        $this->responses = $responses;
    }

    public function downloadAPIFile(
        string $path,
        string $url,
        array  $headers = [],
        array  $options = []
    ): CurlResponse {
        $this->requests[] = [
            'path'    => $path,
            'url'     => $url,
            'headers' => $headers,
            'options' => $options,
        ];
        return $this->responses[$url] ?? new CurlResponse(404, '', []);
    }
}
