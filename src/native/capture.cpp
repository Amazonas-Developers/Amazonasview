#include <pybind11/pybind11.h>
namespace py = pybind11;
using namespace std;



int sumarNumeros(int a, int b){
    return a + b;
}


PYBIND11_MODULE(mimodulo, m) {
    m.doc() = "Ejemplo de módulo en C++ con pybind11";
    m.def("suma", &sumarNumeros, "Función que suma dos enteros");
}