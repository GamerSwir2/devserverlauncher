#include <windows.h>
#include <stdio.h>

#define PORT 55345

BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lParam) {
    SOCKET client_socket = (SOCKET)lParam;
    char title[256];
    if (GetWindowTextA(hwnd, title, sizeof(title)) > 0) {
        strcat_s(title, sizeof(title), "\n");
        send(client_socket, title, (int)strlen(title), 0);
    }
    return TRUE;
}

int main(void) {
    WSADATA wsaData;
    SOCKET listen_socket, client_socket;
    struct sockaddr_in server_addr;

    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
        fprintf(stderr, "WSAStartup failed: %d\n", WSAGetLastError());
        return 1;
    }

    listen_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_socket == INVALID_SOCKET) {
        fprintf(stderr, "socket() failed: %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);

    if (bind(listen_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        fprintf(stderr, "bind() failed: %d\n", WSAGetLastError());
        closesocket(listen_socket);
        WSACleanup();
        return 1;
    }

    if (listen(listen_socket, 1) == SOCKET_ERROR) {
        fprintf(stderr, "listen() failed: %d\n", WSAGetLastError());
        closesocket(listen_socket);
        WSACleanup();
        return 1;
    }

    printf("Waiting for client on port %d...\n", PORT);
    client_socket = accept(listen_socket, NULL, NULL);
    if (client_socket == INVALID_SOCKET) {
        fprintf(stderr, "accept() failed: %d\n", WSAGetLastError());
        closesocket(listen_socket);
        WSACleanup();
        return 1;
    }

    EnumWindows(EnumWindowsProc, (LPARAM)client_socket);

    closesocket(client_socket);
    closesocket(listen_socket);
    WSACleanup();
    return 0;
}
